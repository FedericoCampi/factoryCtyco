#pragma once

#include "CoreMinimal.h"
#include "FactoryTruckGate.h"
#include "FactoryRollDoor.generated.h"

class UMaterialInstanceDynamic;
class USoundBase;
class UStaticMeshComponent;
class UTextRenderComponent;

/**
 * Roll-up door across a trucks' entrance. E at its wall button (on a column) opens it or shuts it; it
 * rolls up into its box and comes down again. While it is not fully open, trucks wait before it. It
 * never comes down on a truck. The actor's origin is the middle of the door's top edge; Button and
 * Housing can be moved on their own.
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryRollDoor : public AFactoryTruckGate
{
    GENERATED_BODY()
public:
    AFactoryRollDoor();
    /** The slatted curtain; its origin is its top edge and it shrinks upward when it rolls up. */
    UPROPERTY(Category="Roll Door", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Door;
    UPROPERTY(Category="Roll Door", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Housing;
    /** Wall button; E within InteractionRadius of it. */
    UPROPERTY(Category="Roll Door", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Button;
    UPROPERTY(Category="Roll Door", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> Prompt;
    /** Size of the doorway it closes (cm). */
    UPROPERTY(Category="Roll Door", EditAnywhere, BlueprintReadOnly) float DoorWidth = 326.0f;
    UPROPERTY(Category="Roll Door", EditAnywhere, BlueprintReadOnly) float DoorHeight = 244.0f;
    UPROPERTY(Category="Roll Door", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.2")) float OpenSeconds = 2.2f;
    UPROPERTY(Category="Roll Door", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="50")) float InteractionRadius = 170.0f;
    UPROPERTY(Category="Roll Door", EditAnywhere, BlueprintReadOnly) TObjectPtr<USoundBase> MoveSound;
    UPROPERTY(Category="Roll Door", VisibleInstanceOnly, BlueprintReadOnly) bool bWantOpen = false;
    /** 0 shut .. 1 open. */
    UPROPERTY(Category="Roll Door", VisibleInstanceOnly, BlueprintReadOnly) float Openness = 0.0f;
    UFUNCTION(BlueprintCallable, Category="Roll Door") bool InReach(const AActor* User) const;
    /** E at the button: opens or shuts; returns whether it did anything. */
    UFUNCTION(BlueprintCallable, Category="Roll Door") bool TryInteract(AActor* User);
    UFUNCTION(BlueprintCallable, Category="Roll Door") void SetOpen(bool bOpen);
    virtual void GetCrossLine(FVector& OutA, FVector& OutB) const override;
    virtual bool IsPassable() const override { return bWantOpen && Openness >= 0.999f; }
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
private:
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> LightMaterial;
    void PlaceDoor();
};
