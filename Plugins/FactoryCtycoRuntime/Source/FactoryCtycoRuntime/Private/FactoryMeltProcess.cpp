#include "FactoryMeltProcess.h"
#include "FactoryDemo.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    const FName HeatParameter(TEXT("Heat"));
    const FName ColorParameter(TEXT("Color"));
    constexpr float DropSeconds = 0.6f;
    /** Points of the curved jet from the last point of the path to the fill. */
    constexpr int32 JetPoints = 10;
    const FLinearColor Hot(1.0f, 0.42f, 0.08f);

    UTextRenderComponent* MakeText(AActor* Owner, const TCHAR* Name, float Size, FColor Color)
    {
        auto* Text = Owner->CreateDefaultSubobject<UTextRenderComponent>(Name);
        Text->SetupAttachment(Owner->GetRootComponent());
        Text->SetUsingAbsoluteScale(true);
        Text->SetHorizontalAlignment(EHTA_Center);
        Text->SetVerticalAlignment(EVRTA_TextCenter);
        Text->SetWorldSize(Size);
        Text->SetTextRenderColor(Color);
        Text->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Text->SetCastShadow(false);
        return Text;
    }

    UPointLightComponent* MakeGlow(AActor* Owner, const TCHAR* Name, float Radius)
    {
        auto* Light = Owner->CreateDefaultSubobject<UPointLightComponent>(Name);
        Light->SetupAttachment(Owner->GetRootComponent());
        Light->SetLightColor(Hot);
        Light->SetIntensity(0.0f);
        Light->SetAttenuationRadius(Radius);
        Light->SetCastShadows(false);
        return Light;
    }
}

AFactoryMeltProcess::AFactoryMeltProcess()
{
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    Stream = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Stream"));
    Stream->SetupAttachment(RootComponent);
    Stream->SetStaticMesh(Cylinder.Object);
    Fill = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Fill"));
    Fill->SetupAttachment(RootComponent);
    Fill->SetStaticMesh(Cube.Object);
    Fill->SetUsingAbsoluteLocation(true);
    Fill->SetUsingAbsoluteRotation(true);
    Fill->SetUsingAbsoluteScale(true);
    Drop = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Drop"));
    Drop->SetupAttachment(RootComponent);
    Drop->SetUsingAbsoluteLocation(true);
    Drop->SetUsingAbsoluteScale(true);
    for (UPrimitiveComponent* Part : {static_cast<UPrimitiveComponent*>(Stream), static_cast<UPrimitiveComponent*>(Fill), static_cast<UPrimitiveComponent*>(Drop)})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetCastShadow(false);
    }
    Fill->SetVisibility(false);
    Drop->SetVisibility(false);
    FurnaceGlow = MakeGlow(this, TEXT("FurnaceGlow"), 800.0f);
    FillGlow = MakeGlow(this, TEXT("FillGlow"), 400.0f);
    FillGlow->SetUsingAbsoluteLocation(true);
    Status = MakeText(this, TEXT("Status"), 28.0f, FColor(255, 236, 214));
    MoldStatus = MakeText(this, TEXT("MoldStatus"), 24.0f, FColor(255, 236, 214));
    MoldStatus->SetUsingAbsoluteLocation(true);
    Prompt = MakeText(this, TEXT("Prompt"), 24.0f, FColor(46, 232, 199));
    Prompt->SetUsingAbsoluteLocation(true);
    Prompt->SetHiddenInGame(true);
}

void AFactoryMeltProcess::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    Status->SetRelativeLocation(MouthPoint + FVector(0, 0, 160));
    FurnaceGlow->SetRelativeLocation(MouthPoint + FVector(0, 0, 40));
    UpdateVisuals();
    // In the editor the whole stream shows, so the path can be placed by eye.
    if (GetWorld() && !GetWorld()->IsGameWorld())
    {
        const TArray<FVector> Path = WorldPourPath();
        float Length = 0.0f;
        for (int32 I = 1; I < Path.Num(); ++I) Length += FVector::Dist(Path[I - 1], Path[I]);
        Front = Length;
        Tail = 0.0f;
        UpdateStream(Path);
        Front = 0.0f;
    }
}

void AFactoryMeltProcess::BeginPlay()
{
    Super::BeginPlay();
    if (MoltenMaterial)
    {
        StreamMaterial = UMaterialInstanceDynamic::Create(MoltenMaterial, this);
        FillMaterial = UMaterialInstanceDynamic::Create(MoltenMaterial, this);
        StreamMaterial->SetScalarParameterValue(HeatParameter, 1.0f);
        Stream->SetMaterial(0, StreamMaterial);
        Fill->SetMaterial(0, FillMaterial);
    }
    if (FeedBelt) FeedBelt->bFeedsProcess = true;
    Stream->ClearInstances();
    // The lid starts at its rest; opening turns it from where it was placed.
    if (LidActor && LidActor->GetRootComponent())
    {
        LidActor->GetRootComponent()->SetMobility(EComponentMobility::Movable);
        LidRest = LidActor->GetRootComponent()->GetRelativeRotation().Quaternion();
        bLidRestKnown = true;
    }
    LidAngle = LidRestAngle;
    ApplyMoltenColor();
    UpdateVisuals();
}

void AFactoryMeltProcess::ApplyMoltenColor()
{
    for (UMaterialInstanceDynamic* Material : {StreamMaterial.Get(), FillMaterial.Get()})
        if (Material) Material->SetVectorParameterValue(ColorParameter, MoltenColor);
    FillGlow->SetLightColor(MoltenColor);
}

void AFactoryMeltProcess::UpdateLid(float DeltaSeconds)
{
    // Off: at rest. On and loading: further open. Melting, molten or pouring: shut.
    const float Goal = Furnace != EFactoryFurnaceStage::Loading ? 0.0f : (bOn ? LidLoadingAngle : LidRestAngle);
    LidAngle = FMath::FInterpConstantTo(LidAngle, Goal, DeltaSeconds, FMath::Max(LidLoadingAngle, 1.0f) / LidSeconds);
    if (!bLidRestKnown || !LidActor || !LidActor->GetRootComponent()) return;
    // A turn about the lid's X (roll), from how it was placed.
    const FQuat Turn = FRotator(0.0f, 0.0f, LidSign * (LidAngle - LidRestAngle)).Quaternion();
    LidActor->GetRootComponent()->SetRelativeRotation(LidRest * Turn);
}

bool AFactoryMeltProcess::SetOn(bool bTurnOn)
{
    if (bTurnOn == bOn || Furnace != EFactoryFurnaceStage::Loading) return false;
    bOn = bTurnOn;
    return true;
}

TArray<FVector> AFactoryMeltProcess::WorldPourPath() const
{
    TArray<FVector> Path;
    for (const FVector& Point : PourPath) Path.Add(GetActorTransform().TransformPosition(Point));
    if (Container && Path.Num() > 0)
    {
        // The last stretch is a jet: it leaves the spout level and falls in a curve onto the fill's surface, which
        // rises as it fills.
        const FVector Center = (FillMin + FillMax) / 2;
        const float Surface = FMath::Lerp(FillMin.Z, FillMax.Z, FillLevel);
        const FVector From = Path.Last(), To = Container->GetActorTransform().TransformPosition(FVector(Center.X, Center.Y, Surface));
        for (int32 I = 1; I <= JetPoints; ++I)
        {
            const float T = static_cast<float>(I) / JetPoints;
            Path.Add(FVector(FMath::Lerp(From.X, To.X, T), FMath::Lerp(From.Y, To.Y, T), FMath::Lerp(From.Z, To.Z, T * T)));
        }
    }
    return Path;
}

bool AFactoryMeltProcess::NearControl(const AActor* User) const
{
    if (!User) return false;
    const FVector Spot = GetActorTransform().TransformPosition(ControlPoint);
    return FVector::DistSquared2D(User->GetActorLocation(), Spot) <= FMath::Square(InteractionRadius)
        && FMath::Abs(User->GetActorLocation().Z - Spot.Z) < 250.0f;
}

bool AFactoryMeltProcess::NearContainer(const AActor* User) const
{
    return User && Container && FVector::DistSquared2D(User->GetActorLocation(), Container->GetActorLocation()) <= FMath::Square(InteractionRadius)
        && FMath::Abs(User->GetActorLocation().Z - Container->GetActorLocation().Z) < 250.0f;
}

bool AFactoryMeltProcess::LightFurnace()
{
    return SetOn(true);
}

bool AFactoryMeltProcess::OpenPour()
{
    if (Furnace != EFactoryFurnaceStage::Molten || Mold != EFactoryMoldStage::Empty) return false;
    Furnace = EFactoryFurnaceStage::Pouring;
    Front = Tail = 0.0f;
    FillLevel = 0.0f;
    return true;
}

bool AFactoryMeltProcess::TakeIngot(AActor* User)
{
    if (Mold != EFactoryMoldStage::IngotReady) return false;
    Mold = EFactoryMoldStage::Empty;
    FillLevel = FillHeat = 0.0f;
    ++IngotsMade;
    if (auto* Inventory = User ? User->FindComponentByClass<UFactoryInventoryComponent>() : nullptr) Inventory->AddItem(IngotResource, 1);
    return true;
}

FString AFactoryMeltProcess::PromptFor(const AActor* User) const
{
    if (NearContainer(User) && Mold == EFactoryMoldStage::IngotReady) return TEXT("[E] RETIRAR LINGOTE");
    if (!NearControl(User)) return FString();
    if (Furnace == EFactoryFurnaceStage::Loading) return bOn ? TEXT("[E] APAGAR HORNO") : TEXT("[E] ENCENDER HORNO");
    if (Furnace == EFactoryFurnaceStage::Molten)
    {
        if (Mold != EFactoryMoldStage::Empty) return TEXT("RETIRÁ EL LINGOTE DEL CONTENEDOR");
        if (!bAutoPour) return TEXT("[E] ABRIR COLADA");
    }
    return FString();
}

bool AFactoryMeltProcess::TryInteract(AActor* User)
{
    if (NearContainer(User) && TakeIngot(User)) return true;
    if (!NearControl(User)) return false;
    if (Furnace == EFactoryFurnaceStage::Loading) return SetOn(!bOn);
    return !bAutoPour && OpenPour();
}

void AFactoryMeltProcess::PullFromBelt()
{
    // Only on, and with the lid open (shut or still opening, what comes waits on the belt).
    if (Furnace != EFactoryFurnaceStage::Loading || !bOn || LidAngle < LidLoadingAngle - 2.0f || !FeedBelt || Loaded >= BatchSize
        || DropLeft > 0.0f) return;
    UFactoryInventoryComponent* Belt = FeedBelt->Input;
    if (!Belt || Belt->GetQuantity(InputItem) < 1 || FeedBelt->ProgressSeconds + KINDA_SMALL_NUMBER < FeedBelt->TravelSeconds()) return;
    // What reaches the end of the belt drops into the mouth.
    const UFactoryResourceDefinition* Item = Belt->Definitions.FindRef(InputItem);
    Belt->RemoveItem(InputItem, 1);
    FeedBelt->ProgressSeconds = 0.0f;
    DropFrom = FeedBelt->OutputPoint();
    DropLeft = DropSeconds;
    Drop->SetStaticMesh(Item ? Item->PickupMesh.Get() : nullptr);
    if (Item)
    {
        MoltenColor = Item->Color;   // the liquid comes out of the colour of what went in
        ApplyMoltenColor();
    }
    if (Item && Item->PickupMesh) Drop->SetWorldScale3D(Item->CargoScale());
}

void AFactoryMeltProcess::StepPour(float DeltaSeconds)
{
    const TArray<FVector> Path = WorldPourPath();
    float Length = 0.0f;
    for (int32 I = 1; I < Path.Num(); ++I) Length += FVector::Dist(Path[I - 1], Path[I]);
    Front = FMath::Min(Length, Front + FlowSpeed * DeltaSeconds);
    if (Front < Length) return;
    if (FillLevel < 1.0f)
    {
        // The liquid reached the container: it fills while the furnace keeps pouring.
        Mold = EFactoryMoldStage::Filling;
        FillHeat = 1.0f;
        FillLevel = FMath::Min(1.0f, FillLevel + DeltaSeconds / FillSeconds);
        return;
    }
    // Full: the furnace is empty and the last of the liquid runs down after it.
    Tail = FMath::Min(Length, Tail + FlowSpeed * DeltaSeconds);
    FurnaceHeat = 1.0f - Tail / FMath::Max(Length, 1.0f);
    if (Tail < Length) return;
    Furnace = EFactoryFurnaceStage::Loading;
    Loaded = 0;
    FurnaceHeat = 0.0f;
    Front = Tail = 0.0f;
    Mold = EFactoryMoldStage::Cooling;
    MoldTime = 0.0f;
}

void AFactoryMeltProcess::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (bAutomatic && !bOn) SetOn(true);
    UpdateLid(DeltaSeconds);
    PullFromBelt();
    if (DropLeft > 0.0f)
    {
        DropLeft -= DeltaSeconds;
        // The batch is in: the lid shuts and it melts (what comes next waits on the belt).
        if (DropLeft <= 0.0f && ++Loaded >= BatchSize)
        {
            Furnace = EFactoryFurnaceStage::Melting;
            StageTime = 0.0f;
        }
    }
    switch (Furnace)
    {
    case EFactoryFurnaceStage::Loading:
        FurnaceHeat = bOn ? 0.15f : 0.0f;   // on: a low glow while it loads
        break;
    case EFactoryFurnaceStage::Ready:   // (older levels) loaded: melt
        Furnace = EFactoryFurnaceStage::Melting;
        StageTime = 0.0f;
        break;
    case EFactoryFurnaceStage::Melting:
        StageTime += DeltaSeconds;
        FurnaceHeat = FMath::Max(0.15f, FMath::Min(1.0f, StageTime / MeltSeconds));
        if (StageTime >= MeltSeconds) Furnace = EFactoryFurnaceStage::Molten;
        break;
    case EFactoryFurnaceStage::Molten:
        FurnaceHeat = 1.0f;
        if (bAutoPour || bAutomatic) OpenPour();
        break;
    case EFactoryFurnaceStage::Pouring:
        StepPour(DeltaSeconds);
        break;
    default:
        break;
    }
    if (Mold == EFactoryMoldStage::Cooling || Mold == EFactoryMoldStage::IngotReady)
    {
        MoldTime += DeltaSeconds;
        FillHeat = FMath::Max(0.0f, 1.0f - MoldTime / CoolSeconds);
        if (Mold == EFactoryMoldStage::Cooling && MoldTime >= CoolSeconds) Mold = EFactoryMoldStage::IngotReady;
        if (bAutomatic && Mold == EFactoryMoldStage::IngotReady && MoldTime >= CoolSeconds + 3.0f) TakeIngot(nullptr);
    }
    UpdateStream(WorldPourPath());
    UpdateVisuals();
}

void AFactoryMeltProcess::UpdateStream(const TArray<FVector>& Path)
{
    Stream->ClearInstances();
    if (Front <= Tail) return;
    float Start = 0.0f;
    for (int32 I = 1; I < Path.Num(); ++I)
    {
        const float Span = FVector::Dist(Path[I - 1], Path[I]);
        const float From = FMath::Max(Tail, Start), To = FMath::Min(Front, Start + Span);
        if (Span > KINDA_SMALL_NUMBER && To - From > 0.5f)
        {
            const FVector Dir = (Path[I] - Path[I - 1]) / Span;
            const FVector A = Path[I - 1] + Dir * (From - Start), B = Path[I - 1] + Dir * (To - Start);
            // The jet and steep stretches fall as a round stream; the rest is a flat ribbon lying in the channel.
            const bool bFalls = I >= PourPath.Num() || FMath::Abs(Dir.Z) > 0.7f;
            FVector Side = FVector::CrossProduct(Dir, FVector::UpVector);
            if (Side.SizeSquared() < 1e-4f) Side = FVector::ForwardVector;
            const FRotator Rotation = FRotationMatrix::MakeFromZX(Dir, Side.GetSafeNormal()).Rotator();
            const float Width = bFalls ? FallWidth : ChannelWidth, Depth = bFalls ? FallWidth : ChannelDepth;
            // A little longer than the stretch, so the joints do not show.
            Stream->AddInstance(FTransform(Rotation, (A + B) / 2, FVector(Width, Depth, (B - A).Size() + 3.0f) / 100.0f), true);
        }
        Start += Span;
    }
}

FString AFactoryMeltProcess::FurnaceText() const
{
    switch (Furnace)
    {
    case EFactoryFurnaceStage::Loading:
        if (!FeedBelt) return TEXT("HORNO · SIN CINTA");
        return bOn ? FString::Printf(TEXT("HORNO ENCENDIDO · CARGANDO %s %d/%d"), *InputLabel, Loaded, BatchSize) : TEXT("HORNO APAGADO");
    case EFactoryFurnaceStage::Ready: return TEXT("HORNO · CARGADO");
    case EFactoryFurnaceStage::Melting:
        return FString::Printf(TEXT("HORNO CERRADO · FUNDIENDO · %d s"), FMath::CeilToInt(FMath::Max(MeltSeconds - StageTime, 0.0f)));
    case EFactoryFurnaceStage::Molten:
        return Mold == EFactoryMoldStage::Empty ? TEXT("FUNDIDO · LISTO PARA COLAR") : TEXT("FUNDIDO · ESPERA EL CONTENEDOR");
    case EFactoryFurnaceStage::Pouring: return TEXT("HORNO · COLANDO");
    }
    return FString();
}

FString AFactoryMeltProcess::MoldText() const
{
    const FString Made = IngotsMade > 0 ? FString::Printf(TEXT("  (%d hechos)"), IngotsMade) : FString();
    switch (Mold)
    {
    case EFactoryMoldStage::Empty: return TEXT("CONTENEDOR VACÍO") + Made;
    case EFactoryMoldStage::Filling: return FString::Printf(TEXT("LLENANDO %d %%"), FMath::RoundToInt(FillLevel * 100));
    case EFactoryMoldStage::Cooling: return FString::Printf(TEXT("ENFRIANDO %d %%"), FMath::RoundToInt((1.0f - FillHeat) * 100));
    case EFactoryMoldStage::IngotReady: return TEXT("LINGOTE DE SILICIO LISTO") + Made;
    }
    return FString();
}

void AFactoryMeltProcess::UpdateVisuals()
{
    const UWorld* World = GetWorld();
    const float Time = World ? World->GetTimeSeconds() : 0.0f;
    const float Flicker = 0.9f + 0.1f * FMath::Sin(Time * 11.0f) * FMath::Sin(Time * 4.3f);
    FurnaceGlow->SetIntensity(GlowIntensity * FMath::Pow(FurnaceHeat, 1.5f) * Flicker);
    FurnaceGlow->SetLightColor(FLinearColor::LerpUsingHSV(Hot, MoltenColor, 0.5f));

    const FVector FillTop(FillMax.X, FillMax.Y, FMath::Lerp(FillMin.Z, FillMax.Z, FillLevel));
    Fill->SetVisibility(Container && FillLevel > 0.01f);
    if (Container)
    {
        const FVector Size = (FillTop - FillMin).ComponentMax(FVector(1.0f));
        Fill->SetWorldTransform(FTransform(FRotator::ZeroRotator, (FillMin + FillTop) / 2, Size / 100.0f) * Container->GetActorTransform());
        const FVector Top = Container->GetActorTransform().TransformPosition(FVector((FillMin.X + FillMax.X) / 2, (FillMin.Y + FillMax.Y) / 2, FillTop.Z));
        FillGlow->SetWorldLocation(Top + FVector(0, 0, 40));
        MoldStatus->SetWorldLocation(Container->GetActorTransform().TransformPosition(FVector(0, 0, FillMax.Z)) + FVector(0, 0, 110));
    }
    FillGlow->SetIntensity(GlowIntensity * 0.3f * FillHeat * FMath::Min(1.0f, FillLevel * 3.0f) * Flicker);
    if (FillMaterial) FillMaterial->SetScalarParameterValue(HeatParameter, FillHeat);
    MoldStatus->SetVisibility(Container != nullptr);

    Status->SetText(FText::FromString(FurnaceText()));
    Status->SetTextRenderColor(FLinearColor::LerpUsingHSV(FLinearColor(1.0f, 0.93f, 0.84f), Hot, FurnaceHeat).ToFColor(true));
    MoldStatus->SetText(FText::FromString(MoldText()));
    MoldStatus->SetTextRenderColor(FLinearColor::LerpUsingHSV(FLinearColor(1.0f, 0.93f, 0.84f), Hot, FillHeat).ToFColor(true));

    // Material dropping from the belt into the mouth, along a small arc.
    Drop->SetVisibility(DropLeft > 0.0f && Drop->GetStaticMesh() != nullptr);
    if (DropLeft > 0.0f)
    {
        const float T = 1.0f - DropLeft / DropSeconds;
        const FVector To = GetActorTransform().TransformPosition(MouthPoint);
        Drop->SetWorldLocation(FMath::Lerp(DropFrom, To, T) + FVector(0, 0, 40.0f * FMath::Sin(T * PI)));
    }

    APlayerController* Player = World ? World->GetFirstPlayerController() : nullptr;
    const APawn* Pawn = Player ? Player->GetPawn() : nullptr;
    const FString Hint = PromptFor(Pawn);
    Prompt->SetHiddenInGame(Hint.IsEmpty());
    if (!Hint.IsEmpty())
    {
        Prompt->SetText(FText::FromString(Hint));
        Prompt->SetWorldLocation(Pawn->GetActorLocation() + FVector(0, 0, 150));
    }
    if (Player && Player->PlayerCameraManager)  // TextRender reads along +X: turn them toward the camera.
    {
        const FVector Camera = Player->PlayerCameraManager->GetCameraLocation();
        for (UTextRenderComponent* Text : {Status.Get(), MoldStatus.Get(), Prompt.Get()})
            Text->SetWorldRotation((Camera - Text->GetComponentLocation()).Rotation());
    }
}
