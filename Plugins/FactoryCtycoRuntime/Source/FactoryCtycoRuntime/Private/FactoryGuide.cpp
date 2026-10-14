#include "FactoryGuide.h"
#include "Components/InputComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EngineUtils.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "FactoryCarry.h"
#include "FactoryDispatchBelt.h"
#include "FactoryElevator.h"
#include "FactoryLoadingBelt.h"
#include "FactoryMission.h"
#include "FactoryRollDoor.h"
#include "FactoryTruckGate.h"
#include "FactoryVehiclePath.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    UStaticMeshComponent* ArrowPart(AActor* Owner, USceneComponent* Parent, const TCHAR* Name, UStaticMesh* Mesh)
    {
        auto* Part = Owner->CreateDefaultSubobject<UStaticMeshComponent>(Name);
        Part->SetupAttachment(Parent);
        Part->SetStaticMesh(Mesh);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetCastShadow(false);
        Part->SetGenerateOverlapEvents(false);
        return Part;
    }
}

AFactoryGuide::AFactoryGuide()
{
    PrimaryActorTick.bCanEverTick = true;
    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);
    // The big arrow: an engine cone (tip down) under a thick shaft; its tip is the Arrow component's origin.
    Arrow = CreateDefaultSubobject<USceneComponent>(TEXT("Arrow"));
    Arrow->SetupAttachment(Root);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cone(TEXT("/Engine/BasicShapes/Cone.Cone"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    Head = ArrowPart(this, Arrow, TEXT("Head"), Cone.Object);
    Head->SetRelativeLocation(FVector(0, 0, 55));
    Head->SetRelativeRotation(FRotator(180, 0, 0));
    Head->SetRelativeScale3D(FVector(1.5f, 1.5f, 1.1f));
    Shaft = ArrowPart(this, Arrow, TEXT("Shaft"), Cylinder.Object);
    Shaft->SetRelativeLocation(FVector(0, 0, 185));
    Shaft->SetRelativeScale3D(FVector(.62f, .62f, 1.5f));

    Slides = {
        {TEXT("2020 · LA PANDEMIA"), TEXT("La fábrica cerró sus puertas"),
         TEXT("Las máquinas se apagaron, los camiones dejaron de venir\ny el polvo cubrió las cintas.")},
        {TEXT("HOY"), TEXT("Volvemos a abrir"),
         TEXT("Los clientes vuelven a llamar. Hay pedidos esperando\ny la fábrica tiene que ponerse en marcha otra vez.")},
        {TEXT("TU NUEVO PUESTO"), TEXT("Sos el gerente"),
         TEXT("Todo depende de vos: encender las líneas, despachar\nlos pedidos y hacer crecer la fábrica, paso a paso.")},
    };
    MissionBody = TEXT("El primer cliente espera su pedido.\nDespachá 20 paquetes en camión desde el despacho.");
}

AFactoryGuide* AFactoryGuide::Find(const UWorld* World)
{
    if (!World) return nullptr;
    for (TActorIterator<AFactoryGuide> It(World); It; ++It) return *It;
    return nullptr;
}

void AFactoryGuide::BeginPlay()
{
    Super::BeginPlay();
    ShownAt = GetWorld()->GetRealTimeSeconds();
    // Unlit orange if the project's material is there; the engine's basic shape material otherwise.
    UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/FactoryCtyco/UI/M_FlechaGuia.M_FlechaGuia"));
    if (!Base) Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
    if (Base)
    {
        ArrowMaterial = UMaterialInstanceDynamic::Create(Base, this);
        ArrowMaterial->SetVectorParameterValue(TEXT("Color"), ArrowColor);
        Head->SetMaterial(0, ArrowMaterial);
        Shaft->SetMaterial(0, ArrowMaterial);
    }
    Arrow->SetVisibility(false, true);
    if (bPaused) { Phase = EPhase::Done; Slide = Slides.Num(); return; }
    if (bSkipIntro || (Slides.IsEmpty() && MissionTitle.IsEmpty())) { StartSteps(); return; }
    if (Slides.IsEmpty()) Phase = EPhase::Briefing;
    // While the story is on screen, its keys come first and the rest of the game waits.
    if (APlayerController* Player = UGameplayStatics::GetPlayerController(this, 0))
    {
        IntroInput = NewObject<UInputComponent>(this, TEXT("GuideIntroInput"));
        IntroInput->Priority = 1000;
        IntroInput->bBlockInput = true;
        IntroInput->BindKey(EKeys::SpaceBar, IE_Pressed, this, &AFactoryGuide::Advance);
        IntroInput->BindKey(EKeys::Enter, IE_Pressed, this, &AFactoryGuide::Advance);
        IntroInput->BindKey(EKeys::LeftMouseButton, IE_Pressed, this, &AFactoryGuide::Advance);
        IntroInput->BindKey(EKeys::Gamepad_FaceButton_Bottom, IE_Pressed, this, &AFactoryGuide::Advance);
        IntroInput->BindKey(EKeys::Tab, IE_Pressed, this, &AFactoryGuide::SkipIntro);
        Player->PushInputComponent(IntroInput);
        Player->SetIgnoreMoveInput(true);
    }
}

void AFactoryGuide::EndPlay(const EEndPlayReason::Type Reason)
{
    EndIntroInput();
    Super::EndPlay(Reason);
}

void AFactoryGuide::EndIntroInput()
{
    if (!IntroInput) return;
    if (APlayerController* Player = UGameplayStatics::GetPlayerController(this, 0))
    {
        Player->PopInputComponent(IntroInput);
        Player->ResetIgnoreMoveInput();
    }
    IntroInput = nullptr;
}

void AFactoryGuide::Advance()
{
    const float Now = GetWorld()->GetRealTimeSeconds();
    // A card needs a moment on screen before it can be passed (a double press would skip it unread).
    if (!IsCovering() || Now - ShownAt < .45f) return;
    if (Phase == EPhase::Intro && ++Slide < Slides.Num()) { ShownAt = Now; return; }
    if (Phase == EPhase::Intro) { Phase = EPhase::Briefing; ShownAt = Now; return; }
    StartSteps();
}

void AFactoryGuide::SkipIntro()
{
    if (IsCovering()) StartSteps();
}

void AFactoryGuide::StartSteps()
{
    EndIntroInput();
    const float Now = GetWorld()->GetRealTimeSeconds();
    IntroEndedAt = Phase == EPhase::Steps ? IntroEndedAt : Now;
    Phase = Steps.IsEmpty() ? EPhase::Done : EPhase::Steps;
    Slide = Slides.Num();
    Step = 0;
    ShownAt = Now;
}

bool AFactoryGuide::IsStepDone(const FFactoryGuideStep& S) const
{
    const UWorld* World = GetWorld();
    const APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0);
    const AActor* Goal = S.GoalActor ? S.GoalActor.Get() : S.ArrowTarget.Get();
    switch (S.Goal)
    {
    case EFactoryGuideGoal::Reach:
    {
        if (!Pawn || !Goal) return false;
        // Arriving by elevator counts once the trip is over (the cabin has come down and opened).
        if (const auto* Elevator = Cast<AFactoryElevator>(Goal); Elevator && !Elevator->IsIdle()) return false;
        return FVector::Dist2D(Pawn->GetActorLocation(), Goal->GetActorLocation()) <= S.Radius
            && FMath::Abs(Pawn->GetActorLocation().Z - Goal->GetActorLocation().Z) < 400.0f;
    }
    case EFactoryGuideGoal::SwitchOnBelt:
        if (const auto* Belt = Cast<AFactoryDispatchBelt>(Goal)) return Belt->bActive;
        for (TActorIterator<AFactoryDispatchBelt> It(World); It; ++It)
            if (It->bActive && !UFactoryUnlockSubsystem::IsLocked(*It)) return true;
        return false;
    case EFactoryGuideGoal::CarryBox:
    {
        const auto* Carry = Pawn ? Pawn->FindComponentByClass<UFactoryCarryComponent>() : nullptr;
        return Carry && Carry->IsCarrying();
    }
    case EFactoryGuideGoal::LoadBox:
    {
        for (TActorIterator<AFactoryLoadingBelt> It(World); It; ++It)
            if (It->GetBoxCount() > 0) return true;
        for (TActorIterator<AFactoryVehiclePath> It(World); It; ++It)
            if (It->GetCargoCount() > 0) return true;
        const auto* Mission = UFactoryMissionSubsystem::Get(this);
        return Mission && Mission->Delivered > 0;
    }
    case EFactoryGuideGoal::Deliver:
    {
        const auto* Mission = UFactoryMissionSubsystem::Get(this);
        return Mission && Mission->bCompleted;
    }
    case EFactoryGuideGoal::OpenGate:
    {
        const auto* Gate = Cast<AFactoryTruckGate>(Goal);
        return Gate && Gate->IsPassable();
    }
    }
    return false;
}

bool AFactoryGuide::GetArrowPoint(FVector& Out) const
{
    const FFactoryGuideStep* S = GetStep();
    if (!S || !S->ArrowTarget || bStepPending) return false;
    FVector Origin, Extent;
    S->ArrowTarget->GetActorBounds(true, Origin, Extent);
    // A roll door is opened at its wall button: the arrow goes there, not over the door.
    if (const auto* Door = Cast<AFactoryRollDoor>(S->ArrowTarget.Get()); Door && Door->Button)
    {
        Origin = Door->Button->Bounds.Origin;
        Extent = Door->Button->Bounds.BoxExtent;
    }
    if (Extent.IsNearlyZero()) { Origin = S->ArrowTarget->GetActorLocation(); Extent = FVector::ZeroVector; }
    Out = FVector(Origin.X, Origin.Y, Origin.Z + Extent.Z + ArrowHeight);
    return true;
}

void AFactoryGuide::UpdateArrow(float Now)
{
    FVector Point;
    const bool bShow = GetArrowPoint(Point);
    Arrow->SetVisibility(bShow, true);
    if (!bShow) return;
    // Bounces over the target: drops fast onto it, squashes a little and rises slow again.
    const float Cycle = FMath::Frac(Now * .9f);
    const float Lift = 55.0f * FMath::Square(FMath::Sin(Cycle * PI));
    const float Squash = Cycle < .12f ? 1.0f - .12f * FMath::Sin(Cycle / .12f * PI) : 1.0f;
    // It grows in when a step starts.
    const float Grow = FMath::Clamp((Now - ShownAt) / .35f, 0.0f, 1.0f);
    const float Pop = Grow < 1.0f ? FMath::Sin(Grow * PI * .5f) * (1.0f + .25f * FMath::Sin(Grow * PI)) : 1.0f;
    Arrow->SetWorldLocation(Point + FVector(0, 0, Lift * ArrowScale));
    Arrow->SetWorldRotation(FRotator(0, Now * 40.0f, 0));
    Arrow->SetWorldScale3D(FVector(ArrowScale * Pop * (2.0f - Squash), ArrowScale * Pop * (2.0f - Squash), ArrowScale * Pop * Squash));
    if (ArrowMaterial) ArrowMaterial->SetScalarParameterValue(TEXT("Brillo"), 1.0f + .6f * FMath::Square(FMath::Sin(Now * 3.0f)));
}

void AFactoryGuide::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const float Now = GetWorld()->GetRealTimeSeconds();
    if (Phase == EPhase::Steps)
    {
        if (bStepPending && Now - StepDoneAt > 1.4f)
        {
            bStepPending = false;
            ShownAt = Now;
            if (++Step >= Steps.Num()) Phase = EPhase::Done;
        }
        else if (!bStepPending && Steps.IsValidIndex(Step) && IsStepDone(Steps[Step]))
        {
            bStepPending = true;
            StepDoneAt = Now;
        }
    }
    UpdateArrow(Now);
}
