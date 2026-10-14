#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryRaisedProp.generated.h"

class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;

/**
 * Scenery in two parts that can be raised: the body (BodyMesh) and its base plate (BaseMesh, from local Z 0 up) sit at
 * the actor, and a solid block (PedestalMesh, concrete) fills the gap from the plate down to the first surface below
 * the actor; no legs, nothing stretched but the block. So moving the actor up raises it; Elevation shows (and sets) the
 * gap to that surface. Scaling it evenly makes it bigger; stretching it in Z beyond its
 * X scale raises it instead (the base's height per unit of extra scale), like the belts.
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryRaisedProp : public AActor
{
    GENERATED_BODY()
public:
    AFactoryRaisedProp();
    UPROPERTY(Category="Raised Prop", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Body;
    UPROPERTY(Category="Raised Prop", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Base;
    UPROPERTY(Category="Raised Prop", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Pedestal;
    UPROPERTY(Category="Raised Prop", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> BodyMesh;
    /** The plate under the body, from local Z 0 up; never stretched. Its XY bounds give the block's footprint. */
    UPROPERTY(Category="Raised Prop", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> BaseMesh;
    /** A 100 cm cube centred on its origin (the engine's by default), stretched to fill the gap under the plate. */
    UPROPERTY(Category="Raised Prop", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> PedestalMesh;
    /** Best world-aligned, so the stretch doesn't show. */
    UPROPERTY(Category="Raised Prop", EditAnywhere, BlueprintReadOnly) TObjectPtr<UMaterialInterface> PedestalMaterial;
    /** How far above the surface under it the actor sits (world cm); the block is that tall. Editing it moves the actor. */
    UPROPERTY(Category="Raised Prop", EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0", Units="Centimeters")) float Elevation = 0;
    UFUNCTION(Category="Raised Prop", BlueprintCallable) void Refresh();
    virtual void OnConstruction(const FTransform& Transform) override;
#if WITH_EDITOR
    virtual void PostEditChangeProperty(FPropertyChangedEvent& Event) override;
#endif
protected:
    virtual void BeginPlay() override;
private:
    /** World Z of the first surface under the actor (ignoring itself), if any. */
    bool FindFloor(float& FloorZ) const;
};
