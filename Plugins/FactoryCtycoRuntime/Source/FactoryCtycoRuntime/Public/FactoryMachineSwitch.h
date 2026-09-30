#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryMachineSwitch.generated.h"

class ULightComponent;
class UMaterialInstanceDynamic;
class USkeletalMeshComponent;
class UTextRenderComponent;

/**
 * Decorative machine turned on and off with E. While off, its animation stops, its lights
 * go dark and every material with a "Power" scalar parameter fades to zero.
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryMachineSwitch : public AActor
{
    GENERATED_BODY()
public:
    AFactoryMachineSwitch();
    UPROPERTY(Category="Machine Switch", EditInstanceOnly, BlueprintReadOnly) TObjectPtr<AActor> Machine;
    /** Lights, screens and lamps that follow the machine's power. */
    UPROPERTY(Category="Machine Switch", EditInstanceOnly, BlueprintReadOnly) TArray<TObjectPtr<AActor>> PoweredActors;
    UPROPERTY(Category="Machine Switch", EditAnywhere, BlueprintReadOnly) FString MachineName = TEXT("EXTRACTOR");
    UPROPERTY(Category="Machine Switch", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="50")) float InteractionRadius = 230.0f;
    /** Seconds the machine takes to spin up or wind down. */
    UPROPERTY(Category="Machine Switch", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.1")) float SpinUpSeconds = 1.5f;
    UPROPERTY(Category="Machine Switch", EditAnywhere, BlueprintReadOnly) bool bStartActive = false;
    UPROPERTY(Category="Machine Switch", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> Prompt;
    UPROPERTY(Category="Machine Switch", VisibleInstanceOnly, BlueprintReadOnly) bool bActive = false;
    UFUNCTION(BlueprintCallable, Category="Machine Switch") void SetMachineOn(bool bOn);
    /** Toggles the machine when the instigator is in reach; returns whether it did. */
    UFUNCTION(BlueprintCallable, Category="Machine Switch") bool TryInteract(AActor* User);
    bool InReach(const AActor* User) const;
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> PowerMaterials;
    UPROPERTY(Transient) TArray<TObjectPtr<ULightComponent>> Lights;
    UPROPERTY(Transient) TArray<TObjectPtr<USkeletalMeshComponent>> Animated;
    TArray<float> LightIntensity;
    float Power = 0.0f;
    void ApplyPower();
};
