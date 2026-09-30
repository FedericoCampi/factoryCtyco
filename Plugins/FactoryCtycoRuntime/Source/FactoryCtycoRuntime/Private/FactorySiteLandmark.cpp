#include "FactorySiteLandmark.h"
#include "FactoryDemo.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

AFactorySiteLandmark::AFactorySiteLandmark()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickGroup = TG_PostUpdateWork;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Visual = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Visual"));
    Visual->SetupAttachment(RootComponent);
    Visual->SetCollisionProfileName(TEXT("NoCollision"));
    Visual->SetCanEverAffectNavigation(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    for (int32 Index = 0; Index < 4; ++Index)
    {
        auto* Piece = CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("Boundary%d"), Index));
        Piece->SetupAttachment(RootComponent);
        Piece->SetStaticMesh(Cube.Object);
        Piece->SetCollisionProfileName(TEXT("NoCollision"));
        Piece->SetCanEverAffectNavigation(false);
        Piece->SetCastShadow(false);
        MarkerPieces.Add(Piece);
    }
    ScanBeam = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("AssemblyScan"));
    ScanBeam->SetupAttachment(RootComponent);
    ScanBeam->SetStaticMesh(Cube.Object);
    ScanBeam->SetCollisionProfileName(TEXT("NoCollision"));
    ScanBeam->SetCanEverAffectNavigation(false);
    ScanBeam->SetCastShadow(false);
    ScanBeam->SetVisibility(false);
    Label = CreateDefaultSubobject<UTextRenderComponent>(TEXT("FloorLabel"));
    Label->SetupAttachment(RootComponent);
    Label->SetHorizontalAlignment(EHTA_Center);
    Label->SetWorldSize(24);
    Label->SetRelativeRotation(FRotator(90, -90, 0));
    Label->SetCastShadow(false);
}

void AFactorySiteLandmark::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    const float X = Footprint.X * .5f, Y = Footprint.Y * .5f;
    for (int32 Index = 0; Index < MarkerPieces.Num(); ++Index)
    {
        const bool bHorizontal = Index < 2;
        const float Sign = Index % 2 == 0 ? -1.0f : 1.0f;
        MarkerPieces[Index]->SetRelativeLocation(bHorizontal ? FVector(0, Sign * Y, 1.4) : FVector(Sign * X, 0, 1.4));
        MarkerPieces[Index]->SetRelativeScale3D(bHorizontal ? FVector(Footprint.X / 100, .035, .018) : FVector(.035, Footprint.Y / 100, .018));
        if (MarkerMaterial) MarkerPieces[Index]->SetMaterial(0, MarkerMaterial);
    }
    ScanBeam->SetRelativeScale3D(FVector(Footprint.X / 100, .055, .035));
    if (MarkerMaterial) ScanBeam->SetMaterial(0, MarkerMaterial);
    Label->SetText(FText::FromString(SiteLabel));
    Label->SetRelativeLocation(FVector(0, -Y + 36, 2));
    Label->SetTextRenderColor(FColor(180, 198, 192));
}

void AFactorySiteLandmark::BeginPlay()
{
    Super::BeginPlay();
    for (TActorIterator<AFactoryDemoWorld> It(GetWorld()); It; ++It) { Factory = *It; break; }
    if (Factory) AddTickPrerequisiteActor(Factory);
    if (MarkerMaterial)
    {
        MarkerMID = UMaterialInstanceDynamic::Create(MarkerMaterial, this);
        for (UStaticMeshComponent* Piece : MarkerPieces) Piece->SetMaterial(0, MarkerMID);
        ScanBeam->SetMaterial(0, MarkerMID);
    }
    UpdateAppearance();
}

void AFactorySiteLandmark::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    UpdateAppearance();
}

void AFactorySiteLandmark::UpdateAppearance()
{
    const bool bEnabled = Factory && Factory->bEnableSiteProgress;
    const bool bComplete = bEnabled && Factory->SiteStage >= RequiredStage;
    const bool bRevealing = bEnabled && Factory->SiteStage + 1 == RequiredStage && Factory->SiteTransitionRemaining > 0;
    RevealAlpha = bComplete ? 1.0f : bRevealing ? FMath::Clamp(1.0f - (Factory->SiteTransitionRemaining - Factory->VisualSubstepSeconds()) / 2.0f, 0.0f, 1.0f) : 0.0f;
    const float Smooth = RevealAlpha * RevealAlpha * (3 - 2 * RevealAlpha);
    Visual->SetVisibility(bComplete || bRevealing);
    Visual->SetRelativeScale3D(FVector(1, 1, FMath::Max(.015f, Smooth)));
    Visual->SetRelativeLocation(FVector(0, 0, bComplete ? 0.0f : (1 - Smooth) * 8));
    ECollisionEnabled::Type Collision = bSolidWhenBuilt && bComplete ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision;
    if (Collision != ECollisionEnabled::NoCollision)
    {
        // The robot can visit an unfinished footprint. Let it leave before the
        // assembled bench becomes solid, including after restoring a save.
        FCollisionObjectQueryParams Objects;
        Objects.AddObjectTypesToQuery(ECC_Pawn);
        FCollisionQueryParams Query(SCENE_QUERY_STAT(SiteAssemblyOccupancy), false, this);
        if (GetWorld()->OverlapAnyTestByObjectType(Visual->Bounds.Origin, FQuat::Identity, Objects,
            FCollisionShape::MakeBox(Visual->Bounds.BoxExtent * .99f), Query)) Collision = ECollisionEnabled::NoCollision;
    }
    if (Visual->GetCollisionEnabled() != Collision)
    {
        if (Collision != ECollisionEnabled::NoCollision) Visual->SetCollisionProfileName(TEXT("BlockAll"));
        Visual->SetCollisionEnabled(Collision);
    }
    const FLinearColor Color = bComplete ? FLinearColor(.045f, .65f, .46f) : bRevealing ? FLinearColor(1, .4f, .035f) : FLinearColor(.24f, .19f, .10f);
    const float Pulse = bRevealing ? 1.4f + .6f * FMath::Sin(GetWorld()->GetTimeSeconds() * 9) : bComplete ? .7f : .04f;
    if (MarkerMID)
    {
        MarkerMID->SetVectorParameterValue(TEXT("BaseColor"), Color);
        MarkerMID->SetVectorParameterValue(TEXT("Emission"), Color * Pulse);
    }
    ScanBeam->SetVisibility(bRevealing);
    ScanBeam->SetRelativeLocation(FVector(0, FMath::Lerp(-Footprint.Y * .5f, Footprint.Y * .5f, RevealAlpha), 3));
    Label->SetTextRenderColor(bComplete ? FColor(95, 230, 202) : bRevealing ? FColor(255, 184, 82) : FColor(133, 139, 139));
}
