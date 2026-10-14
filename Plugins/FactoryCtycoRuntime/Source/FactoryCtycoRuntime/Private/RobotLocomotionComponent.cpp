#include "RobotLocomotionComponent.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/AnimSequence.h"
#include "Animation/BlendSpace.h"
#include "Components/InputComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"

URobotLocomotionComponent::URobotLocomotionComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PrePhysics;
}

void URobotLocomotionComponent::RebuildBlendSpace(UBlendSpace* BlendSpace)
{
#if WITH_EDITOR
    if (BlendSpace)
    {
        BlendSpace->Modify();
        BlendSpace->ValidateSampleData();
        BlendSpace->ResampleData();
        BlendSpace->MarkPackageDirty();
    }
#endif
}

void URobotLocomotionComponent::BeginPlay()
{
    Super::BeginPlay();
    Character = Cast<ACharacter>(GetOwner());
    if (ACharacter* OwnerCharacter = Character.Get())
    {
        AddTickPrerequisiteComponent(OwnerCharacter->GetCharacterMovement());
        OwnerCharacter->GetMesh()->AddTickPrerequisiteComponent(this);
        if (Locomotion)
        {
            OwnerCharacter->GetMesh()->PlayAnimation(Locomotion, true);
        }
        if (bCanJump)
        {
            // The Blueprint turned jumping off (JumpMaxCount 0); this gives it back. Pawn-owned input components are
            // gathered by the PlayerController, under the guide's intro (which blocks them while it is on screen).
            OwnerCharacter->JumpMaxCount = 1;
            OwnerCharacter->GetCharacterMovement()->JumpZVelocity = JumpSpeed;
            JumpInput = NewObject<UInputComponent>(OwnerCharacter, TEXT("RobotJumpInput"));
            JumpInput->RegisterComponent();
            JumpInput->bBlockInput = false;
            JumpInput->BindKey(EKeys::SpaceBar, IE_Pressed, this, &URobotLocomotionComponent::StartJump).bConsumeInput = false;
            JumpInput->BindKey(EKeys::SpaceBar, IE_Released, this, &URobotLocomotionComponent::StopJump).bConsumeInput = false;
        }
    }
}

void URobotLocomotionComponent::StartJump()
{
    ACharacter* OwnerCharacter = Character.Get();
    if (!bCanJump || !OwnerCharacter) return;
    // Not while the movement keys are ignored (intro, cutscenes).
    if (const AController* Controller = OwnerCharacter->GetController(); Controller && Controller->IsMoveInputIgnored()) return;
    OwnerCharacter->GetCharacterMovement()->JumpZVelocity = JumpSpeed;
    OwnerCharacter->Jump();
}

void URobotLocomotionComponent::StopJump()
{
    if (ACharacter* OwnerCharacter = Character.Get()) OwnerCharacter->StopJumping();
}

void URobotLocomotionComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    ACharacter* OwnerCharacter = Character.Get();
    if (!OwnerCharacter || !Locomotion) return;
    APlayerController* Player = Cast<APlayerController>(OwnerCharacter->GetController());
    bFastWalking = Player && Player->IsLocalController() &&
        (Player->IsInputKeyDown(EKeys::LeftShift) || Player->IsInputKeyDown(EKeys::RightShift));
    OwnerCharacter->GetCharacterMovement()->MaxWalkSpeed = bFastWalking ? FastWalkSpeed : WalkSpeed;
    USkeletalMeshComponent* Mesh = OwnerCharacter->GetMesh();
    PlanarSpeed = OwnerCharacter->GetVelocity().Size2D();
    bAirborne = OwnerCharacter->GetCharacterMovement()->IsFalling();
    UBlendSpace* Ground = bCarrying && CarryLocomotion ? CarryLocomotion.Get() : Locomotion.Get();
    UAnimationAsset* Desired = bAirborne && AirbornePose
        ? static_cast<UAnimationAsset*>(AirbornePose.Get())
        : static_cast<UAnimationAsset*>(Ground);
    UAnimSingleNodeInstance* Animation = Mesh->GetSingleNodeInstance();
    if (!Animation || Animation->GetAnimationAsset() != Desired)
    {
        // Picking up or setting down keeps the stride phase, so the legs do not jump.
        const float Position = Animation ? Animation->GetCurrentTime() : 0.0f;
        const bool bSwap = Animation && (Desired == Locomotion || Desired == CarryLocomotion)
            && (Animation->GetAnimationAsset() == Locomotion || Animation->GetAnimationAsset() == CarryLocomotion);
        Mesh->PlayAnimation(Desired, true);
        Animation = Mesh->GetSingleNodeInstance();
        if (Animation && bSwap) Animation->SetPosition(Position, false);
    }
    if (Animation && Desired == Ground)
    {
        Animation->SetBlendSpacePosition(FVector(PlanarSpeed, 0, 0));
        // Scale the authored stride at higher speeds without speeding up idle.
        Animation->SetPlayRate(PlanarSpeed > AuthoredWalkSpeed
            ? FMath::Clamp(PlanarSpeed / FMath::Max(AuthoredWalkSpeed, 1.0f), 1.0f, 3.0f) : 1.0f);
    }
}
