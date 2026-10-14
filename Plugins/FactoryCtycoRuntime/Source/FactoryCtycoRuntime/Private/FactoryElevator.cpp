#include "FactoryElevator.h"
#include "FactoryStaff.h"
#include "FactoryCameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/AudioComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "Kismet/GameplayStatics.h"

namespace
{
    constexpr float BumpSeconds = 0.5f;

    APlayerController* ControllerOf(APawn* Pawn) { return Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr; }

    void FadeCamera(APawn* Pawn, float From, float To, float Seconds)
    {
        if (APlayerController* Player = ControllerOf(Pawn))
            if (Player->PlayerCameraManager) Player->PlayerCameraManager->StartCameraFade(From, To, Seconds, FLinearColor::Black, false, true);
    }

    /** Freezes the rider; the camera arm stops colliding so it does not snap in while inside the shaft. */
    bool FreezeRider(APawn* Pawn)
    {
        if (APlayerController* Player = ControllerOf(Pawn)) Player->SetIgnoreMoveInput(true);
        if (auto* Character = Cast<ACharacter>(Pawn))
        {
            Character->GetCharacterMovement()->StopMovementImmediately();
            Character->GetCharacterMovement()->DisableMovement();
        }
        bool bCollision = true;
        if (auto* Arm = Pawn ? Pawn->FindComponentByClass<USpringArmComponent>() : nullptr)
        {
            bCollision = Arm->bDoCollisionTest;
            Arm->bDoCollisionTest = false;
        }
        return bCollision;
    }

    void ReleaseRider(APawn* Pawn, bool bArmCollision)
    {
        if (APlayerController* Player = ControllerOf(Pawn)) Player->SetIgnoreMoveInput(false);
        if (auto* Character = Cast<ACharacter>(Pawn)) Character->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        if (auto* Arm = Pawn ? Pawn->FindComponentByClass<USpringArmComponent>() : nullptr) Arm->bDoCollisionTest = bArmCollision;
    }

    float Ease(float Alpha) { Alpha = FMath::Clamp(Alpha, 0.0f, 1.0f); return Alpha * Alpha * (3.0f - 2.0f * Alpha); }
}

AFactoryElevator::AFactoryElevator()
{
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    auto MakeMesh = [&](const TCHAR* Name, USceneComponent* Parent, bool bCollide)
    {
        auto* Component = CreateDefaultSubobject<UStaticMeshComponent>(Name);
        Component->SetupAttachment(Parent);
        Component->SetCollisionProfileName(bCollide ? TEXT("BlockAll") : TEXT("NoCollision"));
        return Component;
    };
    // Meshes are assigned per instance (Scripts/apply_elevator2.py, apply_elevator_platform.py).
    Tube = MakeMesh(TEXT("Tube"), RootComponent, false);
    Cabin = MakeMesh(TEXT("Cabin"), RootComponent, true);
    Platform = MakeMesh(TEXT("Platform"), RootComponent, true);
    Platform->SetMobility(EComponentMobility::Movable);
    Panels = MakeMesh(TEXT("Panels"), Cabin, true);
    Roof = MakeMesh(TEXT("Roof"), Cabin, false);
    Roof->SetMobility(EComponentMobility::Movable);
    Roof->SetCastShadow(true);
    for (const TCHAR* Name : {TEXT("DoorRightOuter"), TEXT("DoorRightInner"), TEXT("DoorLeftOuter"), TEXT("DoorLeftInner")})
        Doors.Add(MakeMesh(Name, Cabin, false));
    Motor = CreateDefaultSubobject<UAudioComponent>(TEXT("Motor"));
    Motor->SetupAttachment(Platform);
    Motor->bAutoActivate = false;
    Prompt = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Prompt"));
    Prompt->SetupAttachment(RootComponent);
    Prompt->SetRelativeLocation(FVector(0, 0, 290));
    Prompt->SetHorizontalAlignment(EHTA_Center);
    Prompt->SetVerticalAlignment(EVRTA_TextCenter);
    Prompt->SetWorldSize(24.0f);
    Prompt->SetTextRenderColor(FColor(46, 232, 199));
    Prompt->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Prompt->SetHiddenInGame(true);
}

void AFactoryElevator::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    Cabin->SetRelativeLocation(FVector::ZeroVector);
    SetDepth(0.0f);
    DoorAmount = DoorTarget = 0.0f;
    SetDoors(0.0f);   // shut by default
}

bool AFactoryElevator::InCabin(const AActor* User) const
{
    if (!User) return false;
    const FVector Local = GetActorTransform().InverseTransformPosition(User->GetActorLocation());
    return FMath::Abs(Local.X) <= CabinHalfExtent.X && FMath::Abs(Local.Y) <= CabinHalfExtent.Y
        && Local.Z > -TravelDepth - 50.0f && Local.Z < RiseHeight + 250.0f;
}

TArray<AFactoryElevator*> AFactoryElevator::GetFloors() const
{
    TArray<AFactoryElevator*> Floors;
    for (TActorIterator<AFactoryElevator> It(GetWorld()); It; ++It) Floors.Add(*It);
    Floors.Sort([](const AFactoryElevator& A, const AFactoryElevator& B) { return A.GetActorLocation().Z < B.GetActorLocation().Z; });
    return Floors;
}

int32 AFactoryElevator::GetFloorNumber() const
{
    return GetFloors().IndexOfByKey(this) + 1;
}

AFactoryElevator* AFactoryElevator::FindOpenMenu(const UWorld* World)
{
    if (!World) return nullptr;
    for (TActorIterator<AFactoryElevator> It(World); It; ++It)
        if (It->bMenuOpen) return *It;
    return nullptr;
}

bool AFactoryElevator::TryInteract(AActor* User)
{
    if (!IsIdle() || !InCabin(User)) return false;
    bMenuOpen = !bMenuOpen;
    return true;
}

bool AFactoryElevator::SelectFloor(int32 Number)
{
    const TArray<AFactoryElevator*> Floors = GetFloors();
    APlayerController* Player = GetWorld()->GetFirstPlayerController();
    APawn* Pawn = Player ? Player->GetPawn() : nullptr;
    if (!bMenuOpen || !Floors.IsValidIndex(Number - 1) || !IsIdle() || !Pawn || !InCabin(Pawn)) return false;
    AFactoryElevator* To = Floors[Number - 1];
    if (To == this || !To->IsIdle()) return false;
    bMenuOpen = false;
    Target = To;
    Rider = Pawn;
    bGoingUp = To->GetActorLocation().Z > GetActorLocation().Z;
    const FVector Local = GetActorTransform().InverseTransformPosition(Pawn->GetActorLocation());
    // Keep where they stand, but clear of the walls and the doors.
    RiderOffset = FVector2D(FMath::Clamp(Local.X, 45.0f - CabinHalfExtent.X, CabinHalfExtent.X - 70.0f),
                            FMath::Clamp(Local.Y, 45.0f - CabinHalfExtent.Y, CabinHalfExtent.Y - 45.0f));
    bRiderArmCollision = FreezeRider(Pawn);
    FromDepth = 0.0f;
    ToDepth = bGoingUp ? -RiseHeight : TravelDepth;   // up: it rises in the cabin; down: it sinks into the shaft
    Enter(EPhase::Closing);                           // the doors shut first
    return true;
}

void AFactoryElevator::Arrive(APawn* Pawn, FVector2D Offset, bool bArmCollision, bool bUp)
{
    Rider = Pawn;
    RiderOffset = Offset;
    bRiderArmCollision = bArmCollision;
    // Going up it comes up from the shaft; going down it comes down from above.
    FromDepth = bUp ? TravelDepth : -RiseHeight;
    ToDepth = 0.0f;
    Enter(EPhase::Arriving);
    DoorAmount = DoorTarget = 0.0f;   // shut while the platform comes; they open when it is there
    SetDoors(0.0f);
    SetDepth(FromDepth);
    PlaceRider();
    if (APlayerController* Player = ControllerOf(Pawn)) Player->SetControlRotation(FRotator(0, GetActorRotation().Yaw, 0));
    FadeCamera(Pawn, 1.0f, 0.0f, FadeSeconds);
    if (Motor->Sound) Motor->Play();
}

void AFactoryElevator::Enter(EPhase Next)
{
    Phase = Next;
    Elapsed = 0.0f;
    bFadeStarted = false;
    if (Next == EPhase::Departing)
    {
        Bump(ClunkSound);
        if (Motor->Sound) Motor->Play();
    }
}

void AFactoryElevator::Bump(USoundBase* Sound)
{
    BumpElapsed = 0.0f;
    if (Sound) UGameplayStatics::PlaySoundAtLocation(this, Sound, Platform->GetComponentLocation());
}

void AFactoryElevator::SetDepth(float Depth)
{
    const float Shake = BumpElapsed < BumpSeconds ? 3.0f * FMath::Sin(BumpElapsed * 2.0f * PI * 7.0f) * FMath::Exp(-BumpElapsed * 9.0f) : 0.0f;
    Platform->SetRelativeLocation(FVector(0, 0, Shake - Depth));
    Roof->SetRelativeLocation(FVector(0, 0, Shake - Depth));   // the roof rides with the floor
}

bool AFactoryElevator::DriveDoors(float Goal, float DeltaSeconds)
{
    if (Goal != DoorTarget)
    {
        DoorTarget = Goal;
        if (DoorAmount != Goal && DoorSound) UGameplayStatics::PlaySoundAtLocation(this, DoorSound, Cabin->GetComponentLocation());
    }
    DoorAmount = FMath::FInterpConstantTo(DoorAmount, Goal, DeltaSeconds, 1.0f / DoorSeconds);
    SetDoors(DoorAmount);
    return DoorAmount == Goal;
}

void AFactoryElevator::SetDoors(float OpenAlpha)
{
    // Closed, the outer panel meets the middle and the inner one sits beside it; open, both stack over the post.
    const float Open = DoorOpeningHalf + DoorPanelWidth / 2;
    const float Alpha = Ease(OpenAlpha);
    for (int32 Index = 0; Index < Doors.Num(); ++Index)
    {
        const float Side = Index < 2 ? 1.0f : -1.0f;
        const bool bOuter = Index % 2 == 0;
        const float Closed = DoorPanelWidth * (bOuter ? 0.5f : 1.5f);
        Doors[Index]->SetRelativeLocation(FVector(bOuter ? DoorOuterX : DoorInnerX, Side * FMath::Lerp(Closed, Open, Alpha), 0));
        Doors[Index]->SetRelativeScale3D(FVector(1, Side, 1));  // the orange closing edge faces the middle
    }
}

void AFactoryElevator::PlaceRider() const
{
    APawn* Pawn = Rider.Get();
    if (!Pawn) return;
    const auto* Character = Cast<ACharacter>(Pawn);
    const float HalfHeight = Character ? Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() : 90.0f;
    const float FloorZ = Platform->GetRelativeLocation().Z;
    const FVector Location = GetActorTransform().TransformPosition(FVector(RiderOffset.X, RiderOffset.Y, FloorZ + HalfHeight + 2.0f));
    Pawn->SetActorLocation(Location, false, nullptr, ETeleportType::TeleportPhysics);
}

void AFactoryElevator::Release()
{
    if (APawn* Pawn = Rider.Get()) ReleaseRider(Pawn, bRiderArmCollision);
    Rider.Reset();
}

void AFactoryElevator::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    Elapsed += DeltaSeconds;
    BumpElapsed += DeltaSeconds;
    APlayerController* Player = GetWorld()->GetFirstPlayerController();
    const APawn* Viewer = Player ? Player->GetPawn() : nullptr;
    auto Near = [&](const AActor* Who) { return Who && FVector::DistSquared2D(Who->GetActorLocation(), GetActorLocation()) < FMath::Square(DoorNearRadius)
        && FMath::Abs(Who->GetActorLocation().Z - GetActorLocation().Z) < 300.0f; };
    bool bNear = Near(Viewer);
    for (TActorIterator<AFactoryWorker> It(GetWorld()); It && !bNear; ++It)   // hired workers too
        if (!It->IsHidden()) bNear = Near(*It);
    switch (Phase)
    {
    case EPhase::Idle:
        SetDepth(0.0f);
        DriveDoors(bNear ? 1.0f : 0.0f, DeltaSeconds);   // open while the character is near
        break;
    case EPhase::Closing:
        SetDepth(0.0f);
        if (DriveDoors(0.0f, DeltaSeconds)) Enter(EPhase::Departing);
        break;
    case EPhase::Departing:
        SetDepth(FMath::Lerp(FromDepth, ToDepth, Ease(Elapsed / TravelSeconds)));
        if (Elapsed >= TravelSeconds && !bFadeStarted)
        {
            bFadeStarted = true;
            FadeCamera(Rider.Get(), 0.0f, 1.0f, FadeSeconds);
        }
        if (Elapsed >= TravelSeconds + FadeSeconds)
        {
            AFactoryElevator* To = Target.Get();
            if (APawn* Pawn = Rider.Get(); Pawn && To) To->Arrive(Pawn, RiderOffset, bRiderArmCollision, bGoingUp);
            else Release();
            Rider.Reset();
            // The empty platform goes back to the floor.
            FromDepth = ToDepth;
            ToDepth = 0.0f;
            Enter(EPhase::Returning);
        }
        break;
    case EPhase::Returning:
        SetDepth(FMath::Lerp(FromDepth, ToDepth, Ease(Elapsed / TravelSeconds)));
        if (Elapsed >= TravelSeconds)
        {
            Motor->Stop();
            Bump(ClunkSound);
            Phase = EPhase::Idle;   // the empty platform is back; the doors open if someone comes near
        }
        break;
    case EPhase::Arriving:
        SetDepth(FMath::Lerp(FromDepth, ToDepth, Ease((Elapsed - FadeSeconds) / TravelSeconds)));
        if (Elapsed >= FadeSeconds + TravelSeconds)
        {
            Motor->Stop();
            Bump(ClunkSound);
            Enter(EPhase::Opening);
        }
        break;
    case EPhase::Opening:
        SetDepth(0.0f);
        if (DriveDoors(1.0f, DeltaSeconds))
        {
            Release();   // the rider (if any) walks out once the doors are open
            Phase = EPhase::Idle;
        }
        break;
    }
    if (Phase != EPhase::Idle) PlaceRider();

    const bool bInside = Viewer && InCabin(Viewer);
    if (!bInside || !IsIdle()) bMenuOpen = false;   // walking out closes the panel
    // The roof goes while the player is in the cabin (or riding) so the isometric camera above sees in; in first
    // person the camera is inside and the cabin keeps its roof.
    const UFactoryCameraComponent* View = Viewer ? Viewer->FindComponentByClass<UFactoryCameraComponent>() : nullptr;
    const bool bFirstPerson = View && View->IsFirstPerson();
    Roof->SetVisibility(bFirstPerson || !(bInside || Rider.IsValid()));
    const bool bShow = IsIdle() && bInside && !bMenuOpen;
    Prompt->SetHiddenInGame(!bShow);
    if (!bShow) return;
    Prompt->SetText(FText::FromString(TEXT("[E] ASCENSOR")));
    if (Player->PlayerCameraManager)  // TextRender reads along +X: turn it toward the camera.
        Prompt->SetWorldRotation((Player->PlayerCameraManager->GetCameraLocation() - Prompt->GetComponentLocation()).Rotation());
}
