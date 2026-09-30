#include "RobotLocomotionComponent.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/AnimSequence.h"
#include "Animation/BlendSpace.h"
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
    }
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
