#include "FactoryPresentationComponent.h"
#include "FactoryDemo.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    const FLinearColor Teal(.025f, .72f, .58f);
    const FLinearColor Amber(1.0f, .30f, .025f);
    constexpr float BeltSeconds = .8f;
}

UFactoryPresentationComponent::UFactoryPresentationComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeAsset(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> CylinderAsset(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    Cube = CubeAsset.Object;
    Cylinder = CylinderAsset.Object;
}

void UFactoryPresentationComponent::BeginPlay()
{
    Super::BeginPlay();
    Building = Cast<AFactoryBuilding>(GetOwner());
    for (TActorIterator<AFactoryDemoWorld> It(GetWorld()); It; ++It)
    {
        Factory = *It;
        AddTickPrerequisiteActor(*It);
        break;
    }
    // Runtime construction assigns the definition immediately after SpawnActor.
    // Tick retries once that assignment is complete.
    if (bEnabled) bBuilt = BuildDetails();
}

UMaterialInstanceDynamic* UFactoryPresentationComponent::Material(const FLinearColor& Color,
    float MetallicValue, float RoughnessValue, const FLinearColor& Emission)
{
    AFactoryBuilding* OwnerBuilding = Building.Get();
    auto* Result = UMaterialInstanceDynamic::Create(OwnerBuilding->Definition->PresentationMaterial, this);
    Result->SetVectorParameterValue(TEXT("BaseColor"), Color);
    Result->SetVectorParameterValue(TEXT("Emission"), Emission);
    Result->SetScalarParameterValue(TEXT("Metallic"), MetallicValue);
    Result->SetScalarParameterValue(TEXT("Roughness"), RoughnessValue);
    return Result;
}

UStaticMeshComponent* UFactoryPresentationComponent::Part(UStaticMesh* Mesh, FVector Position,
    FVector Dimensions, UMaterialInstanceDynamic* Surface, FRotator Rotation)
{
    auto* Component = NewObject<UStaticMeshComponent>(GetOwner(), NAME_None, RF_Transient);
    Component->SetupAttachment(GetOwner()->GetRootComponent());
    Component->SetMobility(EComponentMobility::Movable);
    Component->SetStaticMesh(Mesh);
    Component->SetMaterial(0, Surface);
    Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Component->SetGenerateOverlapEvents(false);
    Component->SetCanEverAffectNavigation(false);
    Component->SetRelativeLocation(Position);
    Component->SetRelativeRotation(Rotation);
    Component->SetRelativeScale3D(Dimensions / 100.0);
    Component->SetCastShadow(false);
    Component->RegisterComponent();
    Details.Add(Component);
    DetailCount = Details.Num();
    return Component;
}

bool UFactoryPresentationComponent::BuildDetails()
{
    AFactoryBuilding* B = Building.Get();
    if (!B || !B->Definition || !B->Definition->Mesh || !B->Definition->PresentationMaterial || !Cube || !Cylinder) return false;
    if (B->Definition->DetailBoxMesh) Cube = B->Definition->DetailBoxMesh;
    if (B->Definition->DetailCylinderMesh) Cylinder = B->Definition->DetailCylinderMesh;
    Metal = Material(FLinearColor(.11f, .145f, .16f), .8f, .35f, FLinearColor::Black);
    Rubber = Material(FLinearColor(.021f, .028f, .031f), .05f, .78f, FLinearColor::Black);
    Accent = Material(FLinearColor(.85f, .24f, .035f), .45f, .38f, FLinearColor::Black);
    Signal = Material(Teal * .16f, .25f, .28f, Teal);
    Heat = Material(Amber * .2f, .35f, .32f, Amber);

    // Everything below is placed against the frame, which rides on the platform when there is one.
    const FVector Up(0, 0, B->Lift());
    // A corner shows its own model only: the straight slats and rails would not follow the curve.
    if (B->Definition->Kind == EFactoryBuildingKind::Belt && FMath::Abs(B->Definition->TurnDegrees) >= 0.5f) return true;
    if (B->Definition->Kind == EFactoryBuildingKind::Belt)
    {
        // Slats sit above the existing frame, with short exposed side rollers.
        for (int32 Index = 0; Index < 12; ++Index)
            Slats.Add(Part(Cube, Up + FVector(-88 + Index * 16, 0, 30.5f), FVector(13, 116, 3), Rubber));
        for (float Side : {-1.0f, 1.0f})
        {
            Part(Cube, Up + FVector(0, Side * 66, 31), FVector(196, 5, 8), Metal);
            Part(Cube, Up + FVector(0, Side * 69, 33), FVector(142, 1.8f, 2), Signal);
            for (float X : {-86.0f, 86.0f})
            {
                Part(Cylinder, Up + FVector(X, Side * 64, 19), FVector(15, 15, 12), Metal, FRotator(0, 0, 90));
                Part(Cube, Up + FVector(X, Side * 65, 9), FVector(12, 12, 18), Metal);
                Part(Cube, Up + FVector(X, Side * 69, 31), FVector(15, 3, 9), Accent);
            }
            // Physical arrow at the output edge survives Shipping builds.
            Part(Cube, Up + FVector(82, Side * 56, 35), FVector(15, 2.5f, 1.5f), Signal,
                FRotator(0, Side * -40, 0));
        }
        return true;
    }

    // Bound the imported visual, respecting its authored offset, scale and yaw.
    const FBox Bounds = B->Definition->Mesh->GetBoundingBox().TransformBy(
        FTransform(FRotator(0, B->Definition->MeshYaw, 0), B->Definition->MeshOffset + Up, B->Definition->MeshScale));
    const float Top = Bounds.Max.Z;
    const float Front = Bounds.Max.Y + 3;
    const float CentreX = Bounds.GetCenter().X;
    const float PanelZ = FMath::Clamp(Top * .7f, 45.0f, 115.0f);

    Part(Cube, FVector(CentreX, Front, PanelZ), FVector(49, 4, 21), Rubber);
    Part(Cube, FVector(CentreX - 17, Front + 2.7f, PanelZ + 4), FVector(9, 1.5f, 7), Signal);
    Part(Cube, FVector(CentreX + 7, Front + 2.7f, PanelZ + 5), FVector(24, 1.5f, 2), Metal);
    for (int32 Index = 0; Index < 8; ++Index)
        Gauge.Add(Part(Cube, FVector(CentreX - 18 + Index * 5, Front + 2.7f, PanelZ - 5), FVector(3.5f, 1.5f, 4), Signal));
    // A small status beacon above the machine reads from the isometric camera.
    Part(Cylinder, FVector(CentreX - 25, Bounds.Max.Y - 15, Top + 6), FVector(4, 4, 12), Metal);
    Part(Cylinder, FVector(CentreX - 25, Bounds.Max.Y - 15, Top + 15), FVector(10, 10, 7), Signal);
    Part(Cylinder, FVector(CentreX - 25, Bounds.Max.Y - 15, Top + 20), FVector(11, 11, 3), Metal);

    if (B->Definition->Kind == EFactoryBuildingKind::Processor)
    {
        const bool bSmelter = B->Definition->BuildingId == TEXT("Smelter");
        if (!bSmelter)
        {
            WheelCentre = FVector(CentreX + 25, Front + 5, FMath::Max(24.0f, PanelZ - 30));
            Part(Cylinder, WheelCentre, FVector(38, 38, 7), Rubber, FRotator(0, 0, 90));
            Part(Cylinder, WheelCentre + FVector(0, 5, 0), FVector(12, 12, 5), Accent, FRotator(0, 0, 90));
            for (int32 Index = 0; Index < 4; ++Index)
                Spokes.Add(Part(Cube, WheelCentre, FVector(12, 3, 3), Metal));
        }
        else
        {
            // Three narrow furnace slots and a local, shadowless warm light.
            for (int32 Index = 0; Index < 3; ++Index)
                Part(Cube, FVector(CentreX, Front + 1, PanelZ - 24 - Index * 5), FVector(34, 2, 2.5f), Heat);
            ProcessLight = NewObject<UPointLightComponent>(GetOwner(), NAME_None, RF_Transient);
            ProcessLight->SetupAttachment(GetOwner()->GetRootComponent());
            ProcessLight->SetRelativeLocation(FVector(CentreX, Front + 18, PanelZ - 25));
            ProcessLight->SetMobility(EComponentMobility::Movable);
            ProcessLight->SetCastShadows(false);
            ProcessLight->SetAttenuationRadius(180);
            ProcessLight->SetLightColor(Amber);
            ProcessLight->SetIntensity(0);
            ProcessLight->RegisterComponent();
        }
        SparkOrigin = FVector(Bounds.Max.X * .35f, 0, Top + 3);
        for (int32 Index = 0; Index < 7; ++Index)
        {
            auto* Spark = Part(Cube, SparkOrigin, FVector(1.2f, 1.2f, 4), Heat);
            Spark->SetVisibility(false);
            Sparks.Add(Spark);
        }
    }
    return true;
}

void UFactoryPresentationComponent::UpdateState()
{
    const AFactoryBuilding* B = Building.Get();
    const auto* D = B->Definition.Get();
    if (D->Kind == EFactoryBuildingKind::Processor)
    {
        bBlocked = B->Output->GetFreeSpace() < D->OutputQuantity;
        bWorking = !bBlocked && B->Input->GetQuantity(D->InputItem) >= D->InputQuantity;
    }
    else if (D->Kind == EFactoryBuildingKind::Belt)
    {
        bBlocked = B->Input->GetTotal() > 0 && B->ProgressSeconds >= B->TravelSeconds() - KINDA_SMALL_NUMBER;
        bWorking = B->Input->GetTotal() > 0 && !bBlocked;
    }
    else
    {
        bBlocked = B->Input->GetFreeSpace() == 0;
        bWorking = false;
    }
}

void UFactoryPresentationComponent::TickComponent(float DeltaSeconds, ELevelTick TickType,
    FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(DeltaSeconds, TickType, TickFunction);
    AFactoryBuilding* B = Building.Get();
    if (!B || !B->Definition) return;
    if (bWasEnabled != bEnabled)
    {
        for (UStaticMeshComponent* Detail : Details) Detail->SetVisibility(bEnabled);
        if (!bEnabled)
        {
            B->Visual->SetRelativeLocation(B->Definition->MeshOffset);
            if (ProcessLight) ProcessLight->SetIntensity(0);
        }
        bWasEnabled = bEnabled;
    }
    if (!bEnabled) return;
    if (!bBuilt) { bBuilt = BuildDetails(); if (!bBuilt) return; }
    UpdateState();
    Elapsed += DeltaSeconds;
    Activity = FMath::FInterpTo(Activity, bWorking ? 1.0f : 0.0f, DeltaSeconds, 6);
    MotionPhase = FMath::Fmod(MotionPhase + DeltaSeconds * Activity, 720.0f);
    const float Pulse = .8f + .2f * FMath::Sin(Elapsed * 3.0f);
    const bool bLit = bWorking || (B->Definition->Kind == EFactoryBuildingKind::Storage && B->Input->GetTotal() > 0);
    const FLinearColor StateColor = bBlocked ? Amber : bLit ? Teal : FLinearColor(.10f, .22f, .24f);
    Signal->SetVectorParameterValue(TEXT("BaseColor"), StateColor * .35f);
    Signal->SetVectorParameterValue(TEXT("Emission"), StateColor * (bBlocked ? Pulse * 1.8f : bLit ? 2.2f : .45f));
    const bool bSmelter = B->Definition->BuildingId == TEXT("Smelter");
    Heat->SetVectorParameterValue(TEXT("Emission"), Amber * Activity * (bSmelter ? 4.0f + .8f * FMath::Sin(Elapsed * 11) : 5.0f));

    if (B->Definition->Kind == EFactoryBuildingKind::Belt)
    {
        const float Offset = FMath::Fmod(MotionPhase * (156.0f / BeltSeconds), 16.0f);
        for (int32 Index = 0; Index < Slats.Num(); ++Index)
            Slats[Index]->SetRelativeLocation(FVector(-88 + Index * 16 + Offset - 8, 0, 30.5f + B->Lift()));
        if (B->Cargo->IsVisible() && B->Input->GetTotal() > 0)
        {
            const float Substep = Factory.IsValid() ? Factory->VisualSubstepSeconds() : 0;
            B->PlaceCargo((B->ProgressSeconds + Substep) / B->TravelSeconds());
        }
        return;
    }

    const float Fraction = B->Definition->Kind == EFactoryBuildingKind::Storage
        ? float(B->Input->GetTotal()) / FMath::Max(1, B->Input->Capacity)
        : B->ProgressSeconds / FMath::Max(.1f, B->Definition->CycleSeconds);
    for (int32 Index = 0; Index < Gauge.Num(); ++Index)
        Gauge[Index]->SetMaterial(0, Fraction * Gauge.Num() >= Index + 1 ? Signal.Get() : Metal.Get());
    for (int32 Index = 0; Index < Spokes.Num(); ++Index)
    {
        const float Angle = MotionPhase * 500 + Index * 90;
        const float Radians = FMath::DegreesToRadians(Angle);
        Spokes[Index]->SetRelativeLocation(WheelCentre + FVector(FMath::Cos(Radians) * 11, 5, FMath::Sin(Radians) * 11));
        Spokes[Index]->SetRelativeRotation(FRotator(Angle, 0, 0));
    }
    if (Spokes.Num() > 0)
        B->Visual->SetRelativeLocation(B->Definition->MeshOffset + FVector(0, 0, B->Lift() + FMath::Sin(Elapsed * 46) * Activity * .22f));
    if (ProcessLight) ProcessLight->SetIntensity(Activity * (450 + 45 * FMath::Sin(Elapsed * 11)));
    for (int32 Index = 0; Index < Sparks.Num(); ++Index)
    {
        const float Age = FMath::Fmod(Elapsed * (bSmelter ? .7f : 1.2f) + Index * .137f, 1.6f);
        const bool bShow = bWorking && Age < .45f;
        Sparks[Index]->SetVisibility(bShow);
        if (bShow)
        {
            const float Angle = Index * 2.39996f;
            const FVector Offset(FMath::Cos(Angle) * Age * 44, FMath::Sin(Angle) * Age * 44, Age * 85 - Age * Age * 155);
            Sparks[Index]->SetRelativeLocation(SparkOrigin + Offset);
            Sparks[Index]->SetRelativeRotation(FRotator(Index * 27 + Age * 200, Index * 43, 0));
        }
    }
}
