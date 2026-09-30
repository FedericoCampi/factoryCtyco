#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactorySiteLandmark.generated.h"

class AFactoryDemoWorld;
class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UTextRenderComponent;

/** Authored scenery driven only by the factory's saved progression. */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactorySiteLandmark : public AActor
{
    GENERATED_BODY()
public:
    AFactorySiteLandmark();
    UPROPERTY(Category="Factory Site", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1", ClampMax="3")) int32 RequiredStage = 1;
    UPROPERTY(Category="Factory Site", EditAnywhere, BlueprintReadOnly) FVector2D Footprint = FVector2D(340, 220);
    UPROPERTY(Category="Factory Site", EditAnywhere, BlueprintReadOnly) FString SiteLabel = TEXT("01 / TALLER");
    UPROPERTY(Category="Factory Site", EditAnywhere, BlueprintReadOnly) TObjectPtr<UMaterialInterface> MarkerMaterial;
    UPROPERTY(Category="Factory Site", EditAnywhere, BlueprintReadOnly) bool bSolidWhenBuilt = false;
    UPROPERTY(Category="Factory Site", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Visual;
    UPROPERTY(Category="Factory Site", VisibleAnywhere, BlueprintReadOnly) TArray<TObjectPtr<UStaticMeshComponent>> MarkerPieces;
    UPROPERTY(Category="Factory Site", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> ScanBeam;
    UPROPERTY(Category="Factory Site", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> Label;
    UPROPERTY(Category="Factory Site", VisibleAnywhere, BlueprintReadOnly) float RevealAlpha = 0;
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
private:
    UPROPERTY(Transient) TObjectPtr<AFactoryDemoWorld> Factory;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> MarkerMID;
    void UpdateAppearance();
};
