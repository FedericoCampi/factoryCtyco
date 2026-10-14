#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryMeltProcess.generated.h"

class AFactoryBuilding;
class UFactoryResourceDefinition;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UPointLightComponent;
class UStaticMeshComponent;
class UTextRenderComponent;

UENUM(BlueprintType)
enum class EFactoryFurnaceStage : uint8 { Loading, Ready, Melting, Molten, Pouring };

UENUM(BlueprintType)
enum class EFactoryMoldStage : uint8 { Empty, Filling, Cooling, IngotReady };

/**
 * The furnace's melt. E at the controls turns the furnace on (or off, while it is loading). On, its lid (LidActor) opens
 * further and the belt (FeedBelt) drops material into the mouth until a batch (BatchSize) is in; then the lid shuts
 * and it melts for MeltSeconds while what comes next waits on the belt. Melted, it pours by itself (bAutoPour): the
 * liquid, of the colour of the material it melted (its Color), runs down PourPath (the open discharge pipe and its
 * elbow) and falls into Container, which fills up, cools to grey and leaves an ingot that E takes. Then the lid opens
 * again for the next batch. It only pours into an empty container.
 * Points are in actor space (place the actor at the furnace); drag them in the viewport.
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryMeltProcess : public AActor
{
    GENERATED_BODY()
public:
    AFactoryMeltProcess();
    /** Belt whose output end drops into the furnace's mouth. */
    UPROPERTY(Category="Melt", EditInstanceOnly, BlueprintReadOnly) TObjectPtr<AFactoryBuilding> FeedBelt;
    /** Where the liquid ends up: its fill rises inside FillMin..FillMax (container space). */
    UPROPERTY(Category="Melt", EditInstanceOnly, BlueprintReadOnly) TObjectPtr<AActor> Container;
    UPROPERTY(Category="Melt", EditAnywhere, BlueprintReadOnly) FName InputItem = TEXT("Quartz");
    /** How the furnace calls what it loads («CARGANDO CUARZO 2/4»). */
    UPROPERTY(Category="Melt", EditAnywhere, BlueprintReadOnly) FString InputLabel = TEXT("CUARZO");
    /** Ingot given to whoever takes it out (optional). */
    UPROPERTY(Category="Melt", EditAnywhere, BlueprintReadOnly) TObjectPtr<UFactoryResourceDefinition> IngotResource;
    UPROPERTY(Category="Melt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) int32 BatchSize = 3;
    /** How long a batch melts with the lid shut. */
    UPROPERTY(Category="Melt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.5", Units="Seconds")) float MeltSeconds = 5.0f;
    /** Melted, it pours by itself (into an empty container). Off: E opens the pour. */
    UPROPERTY(Category="Melt", EditAnywhere, BlueprintReadOnly) bool bAutoPour = true;
    /** The furnace's lid (an actor hanging from its hinge, author_horno_tapa.py); it turns about its local X. */
    UPROPERTY(Category="Melt|Lid", EditInstanceOnly, BlueprintReadOnly) TObjectPtr<AActor> LidActor;
    /** How open the lid is in its mesh (degrees): its rest, with the furnace off. */
    UPROPERTY(Category="Melt|Lid", EditAnywhere, BlueprintReadOnly) float LidRestAngle = 38.0f;
    /** How open it is while the furnace is on and loading (degrees); 0 is shut. */
    UPROPERTY(Category="Melt|Lid", EditAnywhere, BlueprintReadOnly) float LidLoadingAngle = 75.0f;
    /** Which way opening turns it about its X, as a roll (+1 or -1; apply_horno_tapa.py measures it). */
    UPROPERTY(Category="Melt|Lid", EditAnywhere, BlueprintReadOnly) float LidSign = 1.0f;
    /** Seconds the lid takes to open or shut fully. */
    UPROPERTY(Category="Melt|Lid", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.1")) float LidSeconds = 1.5f;
    /** How long the container takes to fill once the liquid reaches it. */
    UPROPERTY(Category="Melt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.5", Units="Seconds")) float FillSeconds = 6.0f;
    UPROPERTY(Category="Melt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.5", Units="Seconds")) float CoolSeconds = 12.0f;
    /** How fast the front of the liquid runs down the path (cm/s). */
    UPROPERTY(Category="Melt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="10")) float FlowSpeed = 220.0f;
    /** Without anyone pressing E: lights, pours and empties the container by itself (for when it is automated). */
    UPROPERTY(Category="Melt", EditAnywhere, BlueprintReadOnly) bool bAutomatic = false;
    UPROPERTY(Category="Melt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="50")) float InteractionRadius = 260.0f;

    /** Furnace mouth: where the material drops in and the glow comes from. */
    UPROPERTY(Category="Melt|Points", EditAnywhere, BlueprintReadOnly, meta=(MakeEditWidget="true")) FVector MouthPoint = FVector(0, 0, 450);
    /** Where to stand (on the floor) to light the furnace and open the pour. */
    UPROPERTY(Category="Melt|Points", EditAnywhere, BlueprintReadOnly, meta=(MakeEditWidget="true")) FVector ControlPoint = FVector(250, 0, 0);
    /** The liquid's way from the furnace to the spout, over the liquid's surface. Steep stretches fall as a round
     *  stream; the rest runs flat along the channel. From the last point a curved jet falls onto the fill. */
    UPROPERTY(Category="Melt|Points", EditAnywhere, BlueprintReadOnly, meta=(MakeEditWidget="true")) TArray<FVector> PourPath;
    /** Box the fill rises in, in the container's space (bottom to brim). */
    UPROPERTY(Category="Melt|Container", EditAnywhere, BlueprintReadOnly) FVector FillMin = FVector(-60, -25, 10);
    UPROPERTY(Category="Melt|Container", EditAnywhere, BlueprintReadOnly) FVector FillMax = FVector(60, 25, 48);

    UPROPERTY(Category="Melt|Appearance", EditAnywhere, BlueprintReadOnly) TObjectPtr<UMaterialInterface> MoltenMaterial;
    UPROPERTY(Category="Melt|Appearance", EditAnywhere, BlueprintReadOnly) float ChannelWidth = 20.0f;
    UPROPERTY(Category="Melt|Appearance", EditAnywhere, BlueprintReadOnly) float ChannelDepth = 5.0f;
    UPROPERTY(Category="Melt|Appearance", EditAnywhere, BlueprintReadOnly) float FallWidth = 9.0f;
    /** Furnace glow at full heat. */
    UPROPERTY(Category="Melt|Appearance", EditAnywhere, BlueprintReadOnly) float GlowIntensity = 8000.0f;

    UPROPERTY(Category="Melt", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UPointLightComponent> FurnaceGlow;
    UPROPERTY(Category="Melt", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UPointLightComponent> FillGlow;
    UPROPERTY(Category="Melt", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Stream;
    UPROPERTY(Category="Melt", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Fill;
    UPROPERTY(Category="Melt", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Drop;
    UPROPERTY(Category="Melt", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> Status;
    UPROPERTY(Category="Melt", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> MoldStatus;
    UPROPERTY(Category="Melt", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> Prompt;

    UPROPERTY(Category="Melt", VisibleInstanceOnly, BlueprintReadOnly) EFactoryFurnaceStage Furnace = EFactoryFurnaceStage::Loading;
    UPROPERTY(Category="Melt", VisibleInstanceOnly, BlueprintReadOnly) EFactoryMoldStage Mold = EFactoryMoldStage::Empty;
    UPROPERTY(Category="Melt", VisibleInstanceOnly, BlueprintReadOnly) int32 Loaded = 0;
    UPROPERTY(Category="Melt", VisibleInstanceOnly, BlueprintReadOnly) int32 IngotsMade = 0;
    /** 0..1: furnace heat, how full the container is and how hot its fill still is. */
    UPROPERTY(Category="Melt", VisibleInstanceOnly, BlueprintReadOnly) float FurnaceHeat = 0.0f;
    UPROPERTY(Category="Melt", VisibleInstanceOnly, BlueprintReadOnly) float FillLevel = 0.0f;
    UPROPERTY(Category="Melt", VisibleInstanceOnly, BlueprintReadOnly) float FillHeat = 0.0f;
    /** The furnace is on (E): it loads, melts and pours by itself. */
    UPROPERTY(Category="Melt", VisibleInstanceOnly, BlueprintReadOnly) bool bOn = false;
    /** The colour of the liquid: that of the last material that went in. */
    UPROPERTY(Category="Melt", VisibleInstanceOnly, BlueprintReadOnly) FLinearColor MoltenColor = FLinearColor(1.0f, 0.42f, 0.08f);
    /** How open the lid is now (degrees). */
    UFUNCTION(BlueprintPure, Category="Melt") float GetLidAngle() const { return LidAngle; }
    /** Turns the furnace on or off (only while it is loading). Returns whether it changed. */
    UFUNCTION(BlueprintCallable, Category="Melt") bool SetOn(bool bTurnOn);

    /** Lights the furnace (Ready), opens the pour (Molten, empty container) or takes the ingot out; whichever is
     *  in reach and possible. Returns whether it did something. */
    UFUNCTION(BlueprintCallable, Category="Melt") bool TryInteract(AActor* User);
    /** What E would do for User right now (empty: nothing). */
    UFUNCTION(BlueprintPure, Category="Melt") FString PromptFor(const AActor* User) const;
    /** Turns the furnace on (see SetOn). */
    UFUNCTION(BlueprintCallable, Category="Melt") bool LightFurnace();
    UFUNCTION(BlueprintCallable, Category="Melt") bool OpenPour();
    UFUNCTION(BlueprintCallable, Category="Melt") bool TakeIngot(AActor* User);
    /** The pour path in the world, ending on the fill's surface. */
    UFUNCTION(BlueprintPure, Category="Melt") TArray<FVector> WorldPourPath() const;
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
private:
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> StreamMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FillMaterial;
    float StageTime = 0.0f, MoldTime = 0.0f;
    float LidAngle = 0.0f;
    /** The lid's own rotation (relative to what it hangs from) as placed: the angle turns it from there. */
    FQuat LidRest = FQuat::Identity;
    bool bLidRestKnown = false;
    void UpdateLid(float DeltaSeconds);
    void ApplyMoltenColor();
    /** Pour: distance along the path of the liquid's front and tail (cm). */
    float Front = 0.0f, Tail = 0.0f;
    /** Material dropping from the belt into the mouth (seconds left; <0: none). */
    float DropLeft = -1.0f;
    FVector DropFrom = FVector::ZeroVector;
    bool NearControl(const AActor* User) const;
    bool NearContainer(const AActor* User) const;
    void PullFromBelt();
    void StepPour(float DeltaSeconds);
    void UpdateVisuals();
    void UpdateStream(const TArray<FVector>& Path);
    FString FurnaceText() const;
    FString MoldText() const;
};
