#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Components/ActorComponent.h"
#include "GameFramework/Actor.h"
#include "GameFramework/HUD.h"
#include "FactoryGathering.generated.h"

class UInputComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UInstancedStaticMeshComponent;
class UMaterialInterface;
class UTexture2D;

UCLASS(BlueprintType)
class FACTORYCTYCORUNTIME_API UFactoryResourceDefinition : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Resource") FName ItemId = TEXT("Scrap");
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Resource") FText DisplayName;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Resource") FText Description;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Resource") FLinearColor Color = FLinearColor(1.0f, 0.48f, 0.12f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Resource") TObjectPtr<UTexture2D> Icon;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Resource") TObjectPtr<UStaticMesh> PickupMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Resource") FVector PickupScale = FVector::OneVector;
    /** Size it is shown at on belts, falling into machines and so on: its longest side, cm. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Resource|Size", meta=(ClampMin="1", Units="Centimeters")) float CargoSize = 30.0f;
    /** A piece of another material (a block cut from a rock, gravel crushed from a block): its size is SizePercent of
     *  that one's, so it follows when that one changes. Empty: CargoSize. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Resource|Size") TObjectPtr<UFactoryResourceDefinition> SizeFrom;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Resource|Size", meta=(ClampMin="1", ClampMax="400", Units="Percent")) float SizePercent = 100.0f;
    /** The size it is shown at (cm, longest side), following SizeFrom. */
    UFUNCTION(BlueprintPure, Category="Resource") float GetCargoSize() const;
    /** World scale that shows PickupMesh at GetCargoSize(). */
    FVector CargoScale() const;
};

UCLASS(ClassGroup=(Factory), meta=(BlueprintSpawnableComponent))
class FACTORYCTYCORUNTIME_API UFactoryInventoryComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Inventory", meta=(ClampMin="0")) int32 Capacity = 200;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Inventory") TMap<FName, int32> Items;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Inventory") TMap<FName, TObjectPtr<UFactoryResourceDefinition>> Definitions;
    UFUNCTION(BlueprintPure, Category="Inventory") int32 GetTotal() const;
    UFUNCTION(BlueprintPure, Category="Inventory") int32 GetFreeSpace() const;
    UFUNCTION(BlueprintPure, Category="Inventory") int32 GetQuantity(FName ItemId) const;
    /** Returns only the quantity actually accepted. */
    UFUNCTION(BlueprintCallable, Category="Inventory") int32 AddItem(UFactoryResourceDefinition* Resource, int32 Quantity);
    UFUNCTION(BlueprintCallable, Category="Inventory") int32 RemoveItem(FName ItemId, int32 Quantity);
};

UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryResourcePile : public AActor
{
    GENERATED_BODY()
public:
    AFactoryResourcePile();
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Resource") TObjectPtr<UFactoryResourceDefinition> Resource;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Resource", meta=(ClampMin="0")) int32 Amount = 30;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Resource") FName PersistentId;
    UPROPERTY(EditAnywhere, Category="Appearance") TObjectPtr<UMaterialInterface> MetalMaterial;
    UPROPERTY(EditAnywhere, Category="Appearance") TObjectPtr<UMaterialInterface> AccentMaterial;
    UPROPERTY(EditAnywhere, Category="Appearance") TObjectPtr<UMaterialInterface> FocusMaterial;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Appearance") TObjectPtr<UInstancedStaticMeshComponent> MetalPieces;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Appearance") TObjectPtr<UInstancedStaticMeshComponent> AccentPieces;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Appearance") TObjectPtr<UStaticMeshComponent> CustomVisual;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Appearance") TObjectPtr<UStaticMeshComponent> FocusMarker;
    UFUNCTION(BlueprintCallable, Category="Resource") void RefreshVisuals();
    void SetFocused(bool bFocused);
    int32 TransferTo(UFactoryInventoryComponent* Inventory);
    virtual void OnConstruction(const FTransform& Transform) override;
};

UCLASS(ClassGroup=(Factory), meta=(BlueprintSpawnableComponent))
class FACTORYCTYCORUNTIME_API UFactoryGatheringComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFactoryGatheringComponent();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Gathering") float InteractionDistance = 200.0f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Gathering") TObjectPtr<AFactoryResourcePile> FocusedPile;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Gathering") bool bInventoryOpen = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Gathering") FString Notification;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Gathering") float NotificationUntil = 0.0f;
    UFUNCTION(BlueprintCallable, Category="Gathering") void RefreshTarget();
    UFUNCTION(BlueprintCallable, Category="Gathering") void Interact();
    UFUNCTION(BlueprintCallable, Category="Gathering") void ToggleInventory();
    /** M: music on or off. */
    UFUNCTION(BlueprintCallable, Category="Gathering") void ToggleMusic();
    /** N: the other sounds on or off. */
    UFUNCTION(BlueprintCallable, Category="Gathering") void ToggleSounds();
    bool CanReach(const AFactoryResourcePile* Pile) const;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
private:
    UPROPERTY(Transient) TObjectPtr<UInputComponent> GatheringInput;
};

UCLASS()
class FACTORYCTYCORUNTIME_API AFactoryGatheringHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
};
