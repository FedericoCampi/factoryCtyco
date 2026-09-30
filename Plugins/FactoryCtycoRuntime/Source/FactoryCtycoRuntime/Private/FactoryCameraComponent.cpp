#include "FactoryCameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "FactoryStaff.h"
#include "GameFramework/Character.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputCoreTypes.h"
#include "InputKeyEventArgs.h"

UFactoryCameraComponent::UFactoryCameraComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PrePhysics;
}

void UFactoryCameraComponent::BeginPlay()
{
    Super::BeginPlay();
    SpringArm = GetOwner()->FindComponentByClass<USpringArmComponent>();
    if (USpringArmComponent* Arm = SpringArm.Get())
    {
        InitialDistance = Arm->TargetArmLength;
        InitialOffset = Arm->TargetOffset;
        InitialRotation = Arm->GetComponentRotation();
        DesiredYaw = InitialRotation.Yaw;
        DesiredDistance = InitialDistance;
        Arm->AddTickPrerequisiteComponent(this);
        ArmOverPawn = Arm->GetComponentLocation() - GetOwner()->GetActorLocation();
    }
    Focus = GetOwner()->GetActorLocation();
    LastPawnLocation = Focus;
    if (bStartFree) StopFollowing();
}

bool UFactoryCameraComponent::TargetLocation(const AActor* Target, FVector& Out)
{
    if (!Target) return false;
    if (Target->IsHidden())
    {
        const auto* Worker = Cast<AFactoryWorker>(Target);
        if (Worker && Worker->GetState() == EFactoryWorkerState::Driving && Worker->Car)
        {
            Out = Worker->Car->GetActorLocation();
            return true;
        }
        return false;   // in the elevator: wait until it comes out
    }
    Out = Target->GetActorLocation();
    return true;
}

void UFactoryCameraComponent::Follow(AActor* Target)
{
    USpringArmComponent* Arm = SpringArm.Get();
    if (!Target || !Arm) return;
    FollowTarget = Target;
    bFree = true;   // the arm is placed by hand from now on (on the target)
    Arm->SetUsingAbsoluteLocation(true);
    DesiredPan = FVector::ZeroVector;
}

void UFactoryCameraComponent::StopFollowing()
{
    USpringArmComponent* Arm = SpringArm.Get();
    FollowTarget.Reset();
    bFree = true;
    if (Arm)
    {
        // Keep the view where it is: the focus is what the arm looks at now, panning included.
        Focus = Arm->GetComponentLocation() - ArmOverPawn + Arm->TargetOffset - InitialOffset.RotateAngleAxis(
            FMath::FindDeltaAngleDegrees(InitialRotation.Yaw, Arm->GetComponentRotation().Yaw), FVector::UpVector);
        Arm->SetUsingAbsoluteLocation(true);
        Arm->TargetOffset = InitialOffset.RotateAngleAxis(FMath::FindDeltaAngleDegrees(InitialRotation.Yaw, Arm->GetComponentRotation().Yaw), FVector::UpVector);
        Arm->SetWorldLocation(Focus + ArmOverPawn);
    }
    DesiredPan = FVector::ZeroVector;
}

bool UFactoryCameraComponent::FollowAtScreen(FVector2D ScreenPosition)
{
    ACharacter* Best = CharacterAtScreen(ScreenPosition);
    if (!Best) return false;
    Follow(Best);
    return true;
}

ACharacter* UFactoryCameraComponent::CharacterAtScreen(FVector2D ScreenPosition) const
{
    APlayerController* Player = Controller.Get();
    if (!Player) return nullptr;
    ACharacter* Best = nullptr;
    float BestDistance = PickRadius;
    for (TActorIterator<ACharacter> It(GetWorld()); It; ++It)
    {
        if (It->IsHidden()) continue;
        // The body on screen: a segment from the feet to the head.
        const float Half = It->GetCapsuleComponent() ? It->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() : 90.0f;
        FVector2D Feet, Head;
        if (!Player->ProjectWorldLocationToScreen(It->GetActorLocation() - FVector(0, 0, Half), Feet)
            || !Player->ProjectWorldLocationToScreen(It->GetActorLocation() + FVector(0, 0, Half), Head)) continue;
        const FVector2D Segment = Head - Feet;
        const float T = FMath::Clamp(FVector2D::DotProduct(ScreenPosition - Feet, Segment) / FMath::Max(Segment.SizeSquared(), 1.0f), 0.0f, 1.0f);
        const float Distance = FVector2D::Distance(ScreenPosition, Feet + Segment * T);
        if (Distance < BestDistance) { BestDistance = Distance; Best = *It; }
    }
    return Best;
}

void UFactoryCameraComponent::BindControls(APlayerController* Player)
{
    if (APlayerController* Previous = Controller.Get())
    {
        RemoveTickPrerequisiteActor(Previous);
    }
    Controller = Player;
    if (!Player) return;
    if (!CameraInput)
    {
        CameraInput = NewObject<UInputComponent>(GetOwner(), TEXT("FactoryCameraInput"));
        CameraInput->RegisterComponent();
        CameraInput->bBlockInput = false;
        CameraInput->BindKey(EKeys::MouseScrollUp, IE_Pressed, this, &UFactoryCameraComponent::ZoomIn).bConsumeInput = false;
        CameraInput->BindKey(EKeys::MouseScrollDown, IE_Pressed, this, &UFactoryCameraComponent::ZoomOut).bConsumeInput = false;
        CameraInput->BindKey(EKeys::RightMouseButton, IE_Pressed, this, &UFactoryCameraComponent::StartRightDrag).bConsumeInput = false;
        CameraInput->BindKey(EKeys::Home, IE_Pressed, this, &UFactoryCameraComponent::ResetCamera).bConsumeInput = false;
        CameraInput->BindAxisKey(EKeys::MouseX, this, &UFactoryCameraComponent::PanHorizontal).bConsumeInput = false;
        CameraInput->BindAxisKey(EKeys::MouseY, this, &UFactoryCameraComponent::PanVertical).bConsumeInput = false;
    }
    // PlayerController automatically gathers input components owned by its pawn.
    // Explicitly pushing this component as well would process each event twice.
    AddTickPrerequisiteActor(Player);
}

void UFactoryCameraComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    APawn* Pawn = Cast<APawn>(GetOwner());
    APlayerController* Player = Pawn && Pawn->IsLocallyControlled() ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
    if (Controller.Get() != Player) BindControls(Player);
    KeyPan(DeltaTime);
    if (USpringArmComponent* Arm = SpringArm.Get())
    {
        const FRotator CurrentRotation = Arm->GetComponentRotation();
        const FRotator Rotation = FMath::RInterpTo(CurrentRotation,
            FRotator(InitialRotation.Pitch, DesiredYaw, InitialRotation.Roll), DeltaTime, SmoothingSpeed);
        const float YawStep = FMath::FindDeltaAngleDegrees(CurrentRotation.Yaw, Rotation.Yaw);
        // TargetOffset is world-space. Rotate the entire framing around the pawn,
        // including any pan, so orbiting does not use an off-centre pivot.
        DesiredPan = DesiredPan.RotateAngleAxis(YawStep, FVector::UpVector);
        Arm->TargetOffset = Arm->TargetOffset.RotateAngleAxis(YawStep, FVector::UpVector);
        Arm->SetWorldRotation(Rotation);
        const FVector FramingOffset = InitialOffset.RotateAngleAxis(
            FMath::FindDeltaAngleDegrees(InitialRotation.Yaw, Rotation.Yaw), FVector::UpVector);
        if (bFree)
        {
            // Free: a jump of the own pawn (elevator) takes the camera along; a followed target pulls the focus.
            const FVector PawnNow = GetOwner()->GetActorLocation();
            if (!FollowTarget.IsValid() && FVector::Dist(PawnNow, LastPawnLocation) > 1000.0f) Focus += PawnNow - LastPawnLocation;
            LastPawnLocation = PawnNow;
            FVector Target;
            if (TargetLocation(FollowTarget.Get(), Target))
                Focus = FVector::Dist(Focus, Target) > 2500.0f ? Target : FMath::VInterpTo(Focus, Target, DeltaTime, 8.0f);
            Arm->SetWorldLocation(Focus + ArmOverPawn);
        }
        Arm->TargetArmLength = FMath::FInterpTo(Arm->TargetArmLength, DesiredDistance, DeltaTime, SmoothingSpeed);
        Arm->TargetOffset = FMath::VInterpTo(Arm->TargetOffset, FramingOffset + DesiredPan, DeltaTime, SmoothingSpeed);
        // The character's existing movement Blueprint uses controller yaw for WASD.
        if (Player) Player->SetControlRotation(FRotator(0, Rotation.Yaw, 0));
    }
}

void UFactoryCameraComponent::ZoomIn()
{
    DesiredDistance = FMath::Clamp(DesiredDistance * (1.0f - ZoomFraction), MinimumDistance, MaximumDistance);
}

void UFactoryCameraComponent::ZoomOut()
{
    DesiredDistance = FMath::Clamp(DesiredDistance / (1.0f - ZoomFraction), MinimumDistance, MaximumDistance);
}

void UFactoryCameraComponent::StartRightDrag() { RightDragSincePress = 0.0f; }

bool UFactoryCameraComponent::IsOrbiting() const
{
    const APlayerController* Player = Controller.Get();
    return Player && Player->IsInputKeyDown(EKeys::RightMouseButton);
}

void UFactoryCameraComponent::PanHorizontal(float Value)
{
    if (IsOrbiting())
    {
        RightDragSincePress += FMath::Abs(Value);
        DesiredYaw = FRotator::NormalizeAxis(DesiredYaw + Value * OrbitSensitivity);
    }
    else Pan(Value, 0.0f);
}
void UFactoryCameraComponent::PanVertical(float Value)
{
    if (IsOrbiting()) RightDragSincePress += FMath::Abs(Value);
    else Pan(0.0f, Value);
}

void UFactoryCameraComponent::Pan(float Horizontal, float Vertical)
{
    APlayerController* Player = Controller.Get();
    USpringArmComponent* Arm = SpringArm.Get();
    if (!Player || !Arm || !Player->IsInputKeyDown(EKeys::MiddleMouseButton)) return;
    if (Horizontal == 0.0f && Vertical == 0.0f) return;
    const FRotator Heading(0.0f, Arm->GetComponentRotation().Yaw, 0.0f);
    const FVector Forward = Heading.Vector();
    const FVector Right = FRotationMatrix(Heading).GetUnitAxis(EAxis::Y);
    const float Scale = PanSensitivity * Arm->TargetArmLength / FMath::Max(InitialDistance, 1.0f);
    if (bFree)
    {
        // A free camera slides over the world with no limit; dragging while following lets go of the target.
        if (FollowTarget.IsValid()) StopFollowing();
        Focus -= (Right * Horizontal + Forward * Vertical) * Scale;
        return;
    }
    DesiredPan = (DesiredPan - (Right * Horizontal + Forward * Vertical) * Scale).GetClampedToMaxSize(MaximumPanDistance);
}

void UFactoryCameraComponent::KeyPan(float DeltaTime)
{
    APlayerController* Player = Controller.Get();
    USpringArmComponent* Arm = SpringArm.Get();
    if (!Player || !Arm || KeyPanSpeed <= 0.0f) return;
    const float Forward = (Player->IsInputKeyDown(EKeys::Up) ? 1.0f : 0.0f) - (Player->IsInputKeyDown(EKeys::Down) ? 1.0f : 0.0f);
    const float Side = (Player->IsInputKeyDown(EKeys::Right) ? 1.0f : 0.0f) - (Player->IsInputKeyDown(EKeys::Left) ? 1.0f : 0.0f);
    if (Forward == 0.0f && Side == 0.0f) return;
    // Up goes "into" the screen, Right to the screen's right, whatever the orbit.
    const FRotator Heading(0.0f, Arm->GetComponentRotation().Yaw, 0.0f);
    const FVector Move = (Heading.Vector() * Forward + FRotationMatrix(Heading).GetUnitAxis(EAxis::Y) * Side).GetSafeNormal()
        * KeyPanSpeed * DeltaTime * Arm->TargetArmLength / FMath::Max(InitialDistance, 1.0f);
    if (bFree)
    {
        if (FollowTarget.IsValid()) StopFollowing();
        Focus += Move;
    }
    else DesiredPan = (DesiredPan + Move).GetClampedToMaxSize(MaximumPanDistance);
}

void UFactoryCameraComponent::ResetCamera()
{
    if (bFree) Follow(GetOwner());   // Home: back on the own character
    DesiredDistance = FMath::Clamp(InitialDistance, MinimumDistance, MaximumDistance);
    DesiredPan = FVector::ZeroVector;
    DesiredYaw = InitialRotation.Yaw;
}

void UFactoryCameraComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    BindControls(nullptr);
    if (USpringArmComponent* Arm = SpringArm.Get()) Arm->RemoveTickPrerequisiteComponent(this);
    if (CameraInput) CameraInput->DestroyComponent();
    Super::EndPlay(EndPlayReason);
}

bool UFactoryCameraComponent::SendEditorTestInput(FName KeyName, float Value, bool bPressed)
{
#if WITH_EDITOR
    if (APlayerController* Player = Controller.Get())
    {
        const FKey Key(KeyName);
        if (!Key.IsValid()) return false;
        const EInputEvent Event = Key.IsAnalog() ? IE_Axis : (bPressed ? IE_Pressed : IE_Released);
        return Player->InputKey(FInputKeyEventArgs::CreateSimulated(Key, Event, Value));
    }
#endif
    return false;
}
