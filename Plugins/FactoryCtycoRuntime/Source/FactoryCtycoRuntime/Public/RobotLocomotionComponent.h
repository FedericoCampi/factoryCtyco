#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "RobotLocomotionComponent.generated.h"

class UBlendSpace;
class UAnimSequence;
class ACharacter;

UCLASS(ClassGroup=(Factory), meta=(BlueprintSpawnableComponent))
class FACTORYCTYCORUNTIME_API URobotLocomotionComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    URobotLocomotionComponent();
    UFUNCTION(BlueprintCallable, Category="Robot Animation")
    static void RebuildBlendSpace(UBlendSpace* BlendSpace);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Robot Animation")
    TObjectPtr<UBlendSpace> Locomotion;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Robot Animation")
    TObjectPtr<UAnimSequence> AirbornePose;
    /** Same speeds as Locomotion, with both arms holding a box in front (used while bCarrying). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Robot Animation")
    TObjectPtr<UBlendSpace> CarryLocomotion;
    UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category="Robot Animation")
    bool bCarrying = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Robot Animation", meta=(ClampMin="1.0"))
    float AuthoredWalkSpeed = 220.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Robot Movement", meta=(ClampMin="1.0"))
    float WalkSpeed = 190.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Robot Movement", meta=(ClampMin="1.0"))
    float FastWalkSpeed = 300.0f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Robot Movement")
    bool bFastWalking = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Robot Animation")
    float PlanarSpeed = 0.0f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Robot Animation")
    bool bAirborne = false;
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
private:
    TWeakObjectPtr<ACharacter> Character;
};
