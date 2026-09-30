#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FactoryPresentationComponent.generated.h"

class AFactoryBuilding;
class AFactoryDemoWorld;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class UPointLightComponent;

/** Cosmetic layer. Reads production state; never owns or changes resources. */
UCLASS(ClassGroup=(Factory), meta=(BlueprintSpawnableComponent))
class FACTORYCTYCORUNTIME_API UFactoryPresentationComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFactoryPresentationComponent();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Factory Appearance") bool bEnabled = true;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Factory Appearance") bool bWorking = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Factory Appearance") bool bBlocked = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Factory Appearance") float Activity = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Factory Appearance") float MotionPhase = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Factory Appearance") int32 DetailCount = 0;
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaSeconds, ELevelTick TickType, FActorComponentTickFunction* TickFunction) override;
private:
    TWeakObjectPtr<AFactoryBuilding> Building;
    TWeakObjectPtr<AFactoryDemoWorld> Factory;
    UPROPERTY() TObjectPtr<UStaticMesh> Cube;
    UPROPERTY() TObjectPtr<UStaticMesh> Cylinder;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Details;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Slats;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Spokes;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Gauge;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Sparks;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Metal;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Rubber;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Accent;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Signal;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Heat;
    UPROPERTY(Transient) TObjectPtr<UPointLightComponent> ProcessLight;
    FVector WheelCentre = FVector::ZeroVector;
    FVector SparkOrigin = FVector::ZeroVector;
    float Elapsed = 0;
    bool bBuilt = false;
    bool bWasEnabled = true;
    bool BuildDetails();
    UMaterialInstanceDynamic* Material(const FLinearColor& Color, float Metallic, float Roughness, const FLinearColor& Emission);
    UStaticMeshComponent* Part(UStaticMesh* Mesh, FVector Position, FVector Dimensions,
        UMaterialInstanceDynamic* Surface, FRotator Rotation = FRotator::ZeroRotator);
    void UpdateState();
};
