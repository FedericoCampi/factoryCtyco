#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FactoryHover.generated.h"

class UPrimitiveComponent;
class UMaterialInstanceDynamic;

/**
 * Outlines whatever the mouse is over that a click does something with: a character (the camera follows it),
 * the barrier booth (its panel) and the red "belt full" sign (its detail). The outline is a post-process
 * material on the pawn's camera (/Game/FactoryCtyco/UI/M_ContornoClic) that draws around every mesh rendering
 * custom depth; this component turns custom depth on for the hovered meshes only. The cursor becomes a hand.
 * Added to the player by UFactoryGatheringComponent.
 */
UCLASS(ClassGroup=(Factory), meta=(BlueprintSpawnableComponent))
class FACTORYCTYCORUNTIME_API UFactoryHoverComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFactoryHoverComponent();
    UPROPERTY(Category="Hover", EditAnywhere, BlueprintReadWrite) FLinearColor OutlineColor = FLinearColor(1.0f, .55f, .08f, 1.0f);
    /** Outline thickness in pixels. */
    UPROPERTY(Category="Hover", EditAnywhere, BlueprintReadWrite, meta=(ClampMin="1", ClampMax="8")) float OutlineWidth = 3.0f;
    /** The thing under the mouse that is outlined now, if any. */
    UFUNCTION(BlueprintCallable, Category="Hover") AActor* GetHovered() const { return Hovered.Get(); }

    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Outline;
    TWeakObjectPtr<AActor> Hovered;
    TArray<TWeakObjectPtr<UPrimitiveComponent>> Lit;
    /** What is clickable under the mouse, and the meshes to outline. */
    AActor* FindClickable(TArray<UPrimitiveComponent*>& Parts) const;
    void SetLit(const TArray<UPrimitiveComponent*>& Parts);
};
