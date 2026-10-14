#include "FactoryPlatform.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SplineComponent.h"
#include "Engine/StaticMesh.h"

namespace
{
    constexpr float MinSide = 20.0f;   // between a platform's corner pieces

    UInstancedStaticMeshComponent* MakePieces(AActor* Owner, const TCHAR* Name, USceneComponent* Root)
    {
        auto* Pieces = Owner->CreateDefaultSubobject<UInstancedStaticMeshComponent>(Name);
        Pieces->SetupAttachment(Root);
        Pieces->SetCollisionProfileName(TEXT("BlockAll"));
        Pieces->SetCanEverAffectNavigation(true);
        return Pieces;
    }

    UStaticMesh* LoadPiece(const FString& Folder, const FString& Name)
    {
        return LoadObject<UStaticMesh>(nullptr, *(Folder / Name + TEXT(".") + Name));
    }

    // Rail pieces of the project: folder, span, post, span length, post width, post spacing, floor in the pieces.
    struct FRailStyleInfo { const TCHAR* Folder; const TCHAR* Rail; const TCHAR* Post; float Length, Width, Spacing, Floor; };
    const FRailStyleInfo* StyleInfo(EFactoryRailStyle Style)
    {
        static const FRailStyleInfo Escalera{TEXT("/Game/FactoryCtyco/Environments/Plataformas/Barandas"),
            TEXT("SM_BarandaEscaleraTramo"), TEXT("SM_BarandaEscaleraPoste"), 90.0f, 23.0f, 114.0f, 0.0f};
        static const FRailStyleInfo Verde{TEXT("/Game/FactoryCtyco/Environments/Pasarelas/ModularNuevas/Verde"),
            TEXT("SM_PasarelaVerdeBaranda"), TEXT("SM_PasarelaVerdePoste"), 170.0f, 22.0f, 189.0f, 65.3f};
        static const FRailStyleInfo LElevada{TEXT("/Game/FactoryCtyco/Environments/Pasarelas/ModularNuevas/LElevada"),
            TEXT("SM_PasarelaLElevadaBaranda"), TEXT("SM_PasarelaLElevadaPoste"), 136.0f, 17.0f, 154.0f, 99.7f};
        switch (Style)
        {
        case EFactoryRailStyle::Escalera: return &Escalera;
        case EFactoryRailStyle::Verde: return &Verde;
        case EFactoryRailStyle::LElevada: return &LElevada;
        default: return nullptr;
        }
    }
}

// --- Rail pieces ----------------------------------------------------------------------------------------------------

void FFactoryRailPieces::ApplyStyle(EFactoryRailStyle Style)
{
    const FRailStyleInfo* Info = StyleInfo(Style);
    if (!Info) return;
    RailMesh = LoadPiece(Info->Folder, Info->Rail);
    PostMesh = LoadPiece(Info->Folder, Info->Post);
    RailPieceLength = Info->Length;
    PostWidth = Info->Width;
    PostSpacing = Info->Spacing;
    PieceFloor = Info->Floor;
}

void FFactoryRailPieces::Place(UInstancedStaticMeshComponent* Rails, UInstancedStaticMeshComponent* Posts, FVector2D From,
                               FVector2D To, FVector2D Outside, bool bFirstPost, float Z) const
{
    const float Length = FVector2D::Distance(From, To);
    if (Length < 1.0f || RailPieceLength <= 0.0f) return;
    const FVector2D Dir = (To - From) / Length;
    // The pieces' outside is their -Y: turn them round when it would face in.
    const FVector2D Left(-Dir.Y, Dir.X);
    const bool bFlip = FVector2D::DotProduct(Left, Outside) > 0;
    const FRotator Turn(0, FMath::RadiansToDegrees(FMath::Atan2(Dir.Y, Dir.X)) + (bFlip ? 180.0f : 0.0f), 0);
    const int32 Count = FMath::Max(1, FMath::RoundToInt(Length / FMath::Max(30.0f, PostSpacing)));
    const float Spacing = Length / Count;
    const float Span = FMath::Max(1.0f, Spacing - PostWidth);
    const float Base = Z - PieceFloor;
    for (int32 I = 0; I <= Count; ++I)
        if (I > 0 || bFirstPost) Posts->AddInstance(FTransform(Turn, FVector(From + Dir * (Spacing * I), Base)));
    for (int32 I = 0; I < Count; ++I)
        Rails->AddInstance(FTransform(Turn, FVector(From + Dir * (Spacing * (I + 0.5f)), Base), FVector(Span / RailPieceLength, 1, 1)));
}

// --- Platform -------------------------------------------------------------------------------------------------------

AFactoryPlatform::AFactoryPlatform()
{
    Corners = MakePieces(this, TEXT("Corners"), RootComponent);
    Feet = MakePieces(this, TEXT("Feet"), RootComponent);
    Edges = MakePieces(this, TEXT("Edges"), RootComponent);
    PieceDeckTop = 97.5f;
    PieceLegTop = 32.0f;
}

void AFactoryPlatform::OnConstruction(const FTransform& Transform)
{
    // The project's pieces where none is set (the legs before the height is worked out).
    const FString Folder = PieceFolder();
    if (!CornerMesh) CornerMesh = LoadPiece(Folder, TEXT("SM_PlataformaEsquina"));
    if (!FootMesh) FootMesh = LoadPiece(Folder, TEXT("SM_PlataformaPie"));
    if (!EdgeMesh) EdgeMesh = LoadPiece(Folder, TEXT("SM_PlataformaCostado"));
    if (!LegMesh) LegMesh = LoadPiece(Folder, TEXT("SM_PlataformaColumna"));
    if (RailStyle != EFactoryRailStyle::Propia) RailPieces.ApplyStyle(RailStyle);
    RailMesh = RailPieces.RailMesh;
    PostMesh = RailPieces.PostMesh;
    Super::OnConstruction(Transform);
}

void AFactoryPlatform::ApplyHandles()
{
    const float Least = 2 * CornerSize + MinSide;
    if (Dragged(MinXHandle, Placed[0])) MinX = FMath::Min(MinXHandle.X, MaxX - Least);
    if (Dragged(MaxXHandle, Placed[1])) MaxX = FMath::Max(MaxXHandle.X, MinX + Least);
    if (Dragged(MinYHandle, Placed[2])) MinY = FMath::Min(MinYHandle.Y, MaxY - Least);
    if (Dragged(MaxYHandle, Placed[3])) MaxY = FMath::Max(MaxYHandle.Y, MinY + Least);
    MaxX = FMath::Max(MaxX, MinX + Least);
    MaxY = FMath::Max(MaxY, MinY + Least);
    const float MidX = (MinX + MaxX) / 2, MidY = (MinY + MaxY) / 2, Top = PieceDeckTop + Lift() + 30.0f;
    MinXHandle = Placed[0] = FVector(MinX, MidY, Top);
    MaxXHandle = Placed[1] = FVector(MaxX, MidY, Top);
    MinYHandle = Placed[2] = FVector(MidX, MinY, Top);
    MaxYHandle = Placed[3] = FVector(MidX, MaxY, Top);
}

void AFactoryPlatform::BuildPieces()
{
    Corners->SetStaticMesh(CornerMesh);
    Feet->SetStaticMesh(FootMesh);
    Edges->SetStaticMesh(EdgeMesh);
    Corners->ClearInstances();
    Feet->ClearInstances();
    Edges->ClearInstances();
    const float Up = Lift();
    // The column piece runs from 0 to PieceLegTop - FootTop and stands on the foot: stretched by the lift.
    const float Column = FMath::Max(1.0f, PieceLegTop - FootTop);
    const float ColumnScale = FMath::Max(0.05f, (Column + Up) / Column);
    // Corners: the piece is the +X+Y one, turned for the others.
    const struct { float X, Y, Yaw; } Spots[] = {{MaxX, MaxY, 0}, {MinX, MaxY, 90}, {MinX, MinY, 180}, {MaxX, MinY, 270}};
    for (const auto& S : Spots)
    {
        const FRotator Turn(0, S.Yaw, 0);
        Feet->AddInstance(FTransform(Turn, FVector(S.X, S.Y, 0)));
        Legs->AddInstance(FTransform(Turn, FVector(S.X, S.Y, FootTop), FVector(1, 1, ColumnScale)));
        Corners->AddInstance(FTransform(Turn, FVector(S.X, S.Y, Up)));
    }
    // Side beams between the corners (the piece is the +Y side, along X).
    const float MidX = (MinX + MaxX) / 2, MidY = (MinY + MaxY) / 2;
    const float LengthX = (MaxX - MinX) - 2 * CornerSize, LengthY = (MaxY - MinY) - 2 * CornerSize;
    if (EdgePieceLength > 0 && LengthX > 1)
    {
        const FVector Scale(LengthX / EdgePieceLength, 1, 1);
        Edges->AddInstance(FTransform(FRotator(0, 0, 0), FVector(MidX, MaxY, Up), Scale));
        Edges->AddInstance(FTransform(FRotator(0, 180, 0), FVector(MidX, MinY, Up), Scale));
    }
    if (EdgePieceLength > 0 && LengthY > 1)
    {
        const FVector Scale(LengthY / EdgePieceLength, 1, 1);
        Edges->AddInstance(FTransform(FRotator(0, 270, 0), FVector(MaxX, MidY, Up), Scale));
        Edges->AddInstance(FTransform(FRotator(0, 90, 0), FVector(MinX, MidY, Up), Scale));
    }
    // The deck plate over the whole inside, a little lower so the corners' and sides' own plate shows where they meet.
    if (DeckPieceWidth > 0)
    {
        const float Inset = 8.0f;
        Deck->AddInstance(FTransform(FRotator::ZeroRotator, FVector(MidX, MidY, Up - 0.3f),
            FVector((MaxX - MinX - 2 * Inset) / DeckPieceWidth, (MaxY - MinY - 2 * Inset) / DeckPieceWidth, 1)));
    }
    // Rails: round the edge, each side from the corner before it; the corner post is shared with the side before.
    const float I = RailInset, Floor = PieceDeckTop + Up;
    const FVector2D A(MinX + I, MaxY - I), B(MaxX - I, MaxY - I), C(MaxX - I, MinY + I), D(MinX + I, MinY + I);
    const struct { bool bOn; FVector2D From, To, Outside; } Sides[] = {
        {bRailMaxY, A, B, {0, 1}}, {bRailMaxX, B, C, {1, 0}}, {bRailMinY, C, D, {0, -1}}, {bRailMinX, D, A, {-1, 0}}};
    if (RailPieces.RailMesh && RailPieces.PostMesh)
        for (int32 K = 0; K < 4; ++K)
            if (Sides[K].bOn) RailPieces.Place(Rails, Posts, Sides[K].From, Sides[K].To, Sides[K].Outside, !Sides[(K + 3) % 4].bOn, Floor);
}

// --- Railing --------------------------------------------------------------------------------------------------------

AFactoryRailing::AFactoryRailing()
{
    PrimaryActorTick.bCanEverTick = false;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Path = CreateDefaultSubobject<USplineComponent>(TEXT("Path"));
    Path->SetupAttachment(RootComponent);
    Path->ClearSplinePoints(false);
    Path->AddSplinePoint(FVector::ZeroVector, ESplineCoordinateSpace::Local, false);
    Path->AddSplinePoint(FVector(342.0f, 0, 0), ESplineCoordinateSpace::Local, false);
    Path->SetSplinePointType(0, ESplinePointType::Linear, false);
    Path->SetSplinePointType(1, ESplinePointType::Linear, false);
    Path->UpdateSpline();
    Rails = MakePieces(this, TEXT("Rails"), RootComponent);
    Posts = MakePieces(this, TEXT("Posts"), RootComponent);
}

void AFactoryRailing::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    Rebuild();
}

void AFactoryRailing::Rebuild()
{
    if (Style != EFactoryRailStyle::Propia) Pieces.ApplyStyle(Style);
    // Straight between the points (new points come in curved).
    const int32 Points = Path->GetNumberOfSplinePoints();
    for (int32 P = 0; P < Points; ++P)
        if (Path->GetSplinePointType(P) != ESplinePointType::Linear) Path->SetSplinePointType(P, ESplinePointType::Linear, false);
    Path->SetClosedLoop(bClosed, false);
    Path->UpdateSpline();
    Rails->SetStaticMesh(Pieces.RailMesh);
    Posts->SetStaticMesh(Pieces.PostMesh);
    Rails->ClearInstances();
    Posts->ClearInstances();
    if (!Pieces.RailMesh || !Pieces.PostMesh || Points < 2) return;
    const int32 Segments = bClosed ? Points : Points - 1;
    for (int32 S = 0; S < Segments; ++S)
    {
        const FVector From = Path->GetLocationAtSplinePoint(S, ESplineCoordinateSpace::Local);
        const FVector To = Path->GetLocationAtSplinePoint((S + 1) % Points, ESplineCoordinateSpace::Local);
        const FVector2D Dir = FVector2D(To - From).GetSafeNormal();
        const FVector2D Outside = FVector2D(-Dir.Y, Dir.X) * (bFlip ? -1.0f : 1.0f);
        Pieces.Place(Rails, Posts, FVector2D(From), FVector2D(To), Outside, S == 0 && !bClosed, From.Z);
    }
}
