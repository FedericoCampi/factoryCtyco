#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryBeltStation.generated.h"

class AFactoryBuilding;
class UBoxComponent;
class UFactoryResourceDefinition;
class UPointLightComponent;

/**
 * A station a belt runs through (a tunnel, a washer): what the belt carries changes while it is inside Zone, without
 * stopping. InputItem becomes OutputResource; anything else passes untouched. A short light flash shows each change.
 * Place it over the machine the belt passes through and size Zone to its inside.
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryBeltStation : public AActor
{
    GENERATED_BODY()
public:
    AFactoryBeltStation();
    /** Belts that pass through the station. */
    UPROPERTY(Category="Station", EditInstanceOnly, BlueprintReadOnly) TArray<TObjectPtr<AFactoryBuilding>> Belts;
    UPROPERTY(Category="Station", EditAnywhere, BlueprintReadOnly) FName InputItem;
    UPROPERTY(Category="Station", EditAnywhere, BlueprintReadOnly) TObjectPtr<UFactoryResourceDefinition> OutputResource;
    /** Where the change happens. */
    UPROPERTY(Category="Station", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UBoxComponent> Zone;
    UPROPERTY(Category="Station", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UPointLightComponent> Flash;
    UPROPERTY(Category="Station", EditAnywhere, BlueprintReadOnly) FLinearColor FlashColor = FLinearColor(0.35f, 0.75f, 1.0f);
    UPROPERTY(Category="Station", EditAnywhere, BlueprintReadOnly) float FlashIntensity = 6000.0f;
    /** How many it has changed. */
    UPROPERTY(Category="Station", VisibleInstanceOnly, BlueprintReadOnly) int32 Processed = 0;
    virtual void Tick(float DeltaSeconds) override;
private:
    float FlashLeft = 0.0f;
};
