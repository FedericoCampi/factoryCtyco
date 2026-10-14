#include "FactoryWalkway.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Misc/Paths.h"

namespace
{
    constexpr float MinArm = 30.0f;     // an L's arm past the inner corner
    constexpr float MinLength = 60.0f;  // a straight walkway

    UInstancedStaticMeshComponent* MakeWalkwayPieces(AActor* Owner, const TCHAR* Name, USceneComponent* Root)
    {
        auto* Pieces = Owner->CreateDefaultSubobject<UInstancedStaticMeshComponent>(Name);
        Pieces->SetupAttachment(Root);
        Pieces->SetCollisionProfileName(TEXT("BlockAll"));
        Pieces->SetCanEverAffectNavigation(true);
        return Pieces;
    }
}

AFactoryWalkway::AFactoryWalkway()
{
    PrimaryActorTick.bCanEverTick = false;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Deck = MakeWalkwayPieces(this, TEXT("Deck"), RootComponent);
    Rails = MakeWalkwayPieces(this, TEXT("Rails"), RootComponent);
    Posts = MakeWalkwayPieces(this, TEXT("Posts"), RootComponent);
    Legs = MakeWalkwayPieces(this, TEXT("Legs"), RootComponent);
}

void AFactoryWalkway::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    ApplyHeight();
    ApplyHandles();
    Rebuild();
}

float AFactoryWalkway::Lift() const
{
    return LegMesh && PieceLegTop > 0.0f ? DeckHeight - PieceDeckTop : 0.0f;
}

void AFactoryWalkway::ApplyHeight()
{
    if (!LegMesh || PieceLegTop <= 0.0f)
    {
        HeightHandle = PlacedHeight = FVector::ZeroVector;
        return;
    }
    if (Dragged(HeightHandle, PlacedHeight)) DeckHeight = HeightHandle.Z;
    if (DeckHeight <= 0.0f) DeckHeight = PieceDeckTop;
    // At least 5 cm of legs under the deck.
    DeckHeight = FMath::Clamp(DeckHeight, PieceDeckTop - PieceLegTop + 5.0f, MaxDeckHeight);
    HeightHandle = PlacedHeight = FVector(HeightHandleAt(), DeckHeight);
}

void AFactoryWalkway::Rebuild()
{
    auto OrDefault = [this](TObjectPtr<UStaticMesh>& Mesh, const TCHAR* Piece)
    {
        if (!Mesh)
        {
            const FString Name = PiecePrefix() + Piece;
            const FString Path = PieceFolder() / Name + TEXT(".") + FPaths::GetCleanFilename(Name);
            Mesh = LoadObject<UStaticMesh>(nullptr, *Path);
        }
    };
    OrDefault(DeckMesh, TEXT("Piso"));
    OrDefault(RailMesh, TEXT("Baranda"));
    OrDefault(PostMesh, TEXT("Poste"));
    Deck->SetStaticMesh(DeckMesh);
    Rails->SetStaticMesh(RailMesh);
    Posts->SetStaticMesh(PostMesh);
    Legs->SetStaticMesh(LegMesh);
    Deck->ClearInstances();
    Rails->ClearInstances();
    Posts->ClearInstances();
    Legs->ClearInstances();
    BuildPieces();
}

void AFactoryWalkway::AddDeck(FVector2D From, FVector2D To, float Width)
{
    const float Length = FVector2D::Distance(From, To);
    if (Length < 1.0f || DeckPieceSize.X <= 0 || DeckPieceSize.Y <= 0) return;
    const FVector2D Dir = (To - From) / Length;
    const float Yaw = FMath::RadiansToDegrees(FMath::Atan2(Dir.Y, Dir.X));
    // Whole pieces, stretched a little to fill the length.
    const int32 Count = FMath::Max(1, FMath::RoundToInt(Length / DeckPieceSize.X));
    const float Each = Length / Count;
    const float Up = Lift();
    // The legs go from the ground to the deck: stretched (or squeezed) by how much the deck went up or down.
    const bool bLegs = LegMesh && PieceLegTop > 0.0f;
    const float LegScale = bLegs ? (PieceLegTop + Up) / PieceLegTop : 1.0f;
    for (int32 I = 0; I < Count; ++I)
    {
        const FVector2D At = From + Dir * (Each * (I + 0.5f));
        const FVector Scale(Each / DeckPieceSize.X, Width / DeckPieceSize.Y, 1);
        Deck->AddInstance(FTransform(FRotator(0, Yaw, 0), FVector(At, Up), Scale));
        if (bLegs) Legs->AddInstance(FTransform(FRotator(0, Yaw, 0), FVector(At, 0), FVector(Scale.X, Scale.Y, LegScale)));
    }
}

void AFactoryWalkway::AddRail(FVector2D From, FVector2D To, FVector2D Outside, bool bFirstPost)
{
    const float Length = FVector2D::Distance(From, To);
    if (Length < 1.0f) return;
    const FVector2D Dir = (To - From) / Length;
    // The pieces' outside is their -Y: turn them round when it would face in.
    const FVector2D Left(-Dir.Y, Dir.X);
    const bool bFlip = FVector2D::DotProduct(Left, Outside) > 0;
    const FRotator Turn(0, FMath::RadiansToDegrees(FMath::Atan2(Dir.Y, Dir.X)) + (bFlip ? 180.0f : 0.0f), 0);
    const int32 Count = FMath::Max(1, FMath::RoundToInt(Length / PostSpacing));
    const float Spacing = Length / Count;
    const float Span = FMath::Max(1.0f, Spacing - PostWidth);
    const float Up = Lift();
    for (int32 I = 0; I <= Count; ++I)
        if (I > 0 || bFirstPost) Posts->AddInstance(FTransform(Turn, FVector(From + Dir * (Spacing * I), Up)));
    for (int32 I = 0; I < Count; ++I)
    {
        const FVector2D At = From + Dir * (Spacing * (I + 0.5f));
        Rails->AddInstance(FTransform(Turn, FVector(At, Up), FVector(Span / RailPieceLength, 1, 1)));
    }
}

// --- L --------------------------------------------------------------------------------------------------------------

void AFactoryWalkwayL::ApplyHandles()
{
    // Each handle only moves its rail across (or its end along): the other components are ignored.
    if (Dragged(OuterRailAHandle, Placed[0])) OuterA = FMath::Min(OuterRailAHandle.Y, InnerA - MinWidth);
    if (Dragged(InnerRailAHandle, Placed[1])) InnerA = FMath::Max(InnerRailAHandle.Y, OuterA + MinWidth);
    if (Dragged(OuterRailBHandle, Placed[2])) OuterB = FMath::Min(OuterRailBHandle.X, InnerB - MinWidth);
    if (Dragged(InnerRailBHandle, Placed[3])) InnerB = FMath::Max(InnerRailBHandle.X, OuterB + MinWidth);
    if (Dragged(EndAHandle, Placed[4])) EndA = EndAHandle.X;
    if (Dragged(EndBHandle, Placed[5])) EndB = EndBHandle.Y;
    // Typed values too: the rails stay apart and the arms reach past the inner corner.
    InnerA = FMath::Max(InnerA, OuterA + MinWidth);
    InnerB = FMath::Max(InnerB, OuterB + MinWidth);
    EndA = FMath::Max(EndA, InnerB + MinArm);
    EndB = FMath::Max(EndB, InnerA + MinArm);
    const float MidA = (InnerB + EndA) / 2, MidB = (InnerA + EndB) / 2, Top = 100.0f + Lift();
    OuterRailAHandle = Placed[0] = FVector(MidA, OuterA, Top);
    InnerRailAHandle = Placed[1] = FVector(MidA, InnerA, Top);
    OuterRailBHandle = Placed[2] = FVector(OuterB, MidB, Top);
    InnerRailBHandle = Placed[3] = FVector(InnerB, MidB, Top);
    EndAHandle = Placed[4] = FVector(EndA, (OuterA + InnerA) / 2, Top / 2);
    EndBHandle = Placed[5] = FVector((OuterB + InnerB) / 2, EndB, Top / 2);
}

void AFactoryWalkwayL::BuildPieces()
{
    // Deck: arm A along X over the corner, arm B along Y from where arm A's deck ends (they do not overlap).
    const float Past = DeckPastRail;
    const float MidAY = (OuterA + InnerA) / 2, MidBX = (OuterB + InnerB) / 2;
    AddDeck({OuterB - Past, MidAY}, {EndA, MidAY}, InnerA - OuterA + 2 * Past);
    AddDeck({MidBX, InnerA + Past}, {MidBX, EndB}, InnerB - OuterB + 2 * Past);
    // Rails: the corner posts are shared, so arm B's rails leave out their first one when arm A's is there.
    const FVector2D Outer(OuterB, OuterA), Inner(InnerB, InnerA);
    if (bOuterRailA) AddRail(Outer, {EndA, OuterA}, {0, -1}, true);
    if (bInnerRailA) AddRail(Inner, {EndA, InnerA}, {0, 1}, true);
    if (bOuterRailB) AddRail(Outer, {OuterB, EndB}, {-1, 0}, !bOuterRailA);
    if (bInnerRailB) AddRail(Inner, {InnerB, EndB}, {1, 0}, !bInnerRailA);
}

// --- Straight -------------------------------------------------------------------------------------------------------

AFactoryWalkwayStraight::AFactoryWalkwayStraight()
{
    DeckPieceSize = FVector2D(116.0f, 250.2f);
    DeckPastRail = 15.0f;
    RailPieceLength = 116.0f;
    PostWidth = 24.0f;
    PostSpacing = 140.0f;
}

void AFactoryWalkwayStraight::ApplyHandles()
{
    if (Dragged(LeftRailHandle, Placed[0])) LeftRailY = FMath::Min(LeftRailHandle.Y, RightRailY - MinWidth);
    if (Dragged(RightRailHandle, Placed[1])) RightRailY = FMath::Max(RightRailHandle.Y, LeftRailY + MinWidth);
    if (Dragged(StartHandle, Placed[2])) StartX = FMath::Min(StartHandle.X, EndX - MinLength);
    if (Dragged(EndHandle, Placed[3])) EndX = FMath::Max(EndHandle.X, StartX + MinLength);
    RightRailY = FMath::Max(RightRailY, LeftRailY + MinWidth);
    EndX = FMath::Max(EndX, StartX + MinLength);
    const float MidX = (StartX + EndX) / 2, MidY = (LeftRailY + RightRailY) / 2, Top = 100.0f + Lift();
    LeftRailHandle = Placed[0] = FVector(MidX, LeftRailY, Top);
    RightRailHandle = Placed[1] = FVector(MidX, RightRailY, Top);
    StartHandle = Placed[2] = FVector(StartX, MidY, Top / 2);
    EndHandle = Placed[3] = FVector(EndX, MidY, Top / 2);
}

void AFactoryWalkwayStraight::BuildPieces()
{
    const float MidY = (LeftRailY + RightRailY) / 2;
    AddDeck({StartX, MidY}, {EndX, MidY}, RightRailY - LeftRailY + 2 * DeckPastRail);
    if (bLeftRail) AddRail({StartX, LeftRailY}, {EndX, LeftRailY}, {0, -1}, true);
    if (bRightRail) AddRail({StartX, RightRailY}, {EndX, RightRailY}, {0, 1}, true);
}
