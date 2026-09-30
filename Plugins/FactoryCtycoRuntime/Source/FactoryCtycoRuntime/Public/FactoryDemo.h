#pragma once

#include "CoreMinimal.h"
#include "FactoryGathering.h"
#include "GameFramework/SaveGame.h"
#include "FactoryDemo.generated.h"

class UBoxComponent;
class UInputComponent;
class UInstancedStaticMeshComponent;
class AFactoryDemoWorld;
class UFactoryPresentationComponent;

UENUM(BlueprintType)
enum class EFactoryBuildingKind : uint8 { Processor, Storage, Belt };

/** Authored data, independent of the runtime inventories and visual meshes. */
UCLASS(BlueprintType)
class FACTORYCTYCORUNTIME_API UFactoryBuildingDefinition : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) FName BuildingId;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) FText DisplayName;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) EFactoryBuildingKind Kind = EFactoryBuildingKind::Storage;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> Mesh;
    UPROPERTY(Category="Factory Demo|Appearance", EditAnywhere, BlueprintReadOnly) TObjectPtr<UMaterialInterface> PresentationMaterial;
    UPROPERTY(Category="Factory Demo|Appearance", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> DetailBoxMesh;
    UPROPERTY(Category="Factory Demo|Appearance", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> DetailCylinderMesh;
    /** Platform under the building. Its mesh is stretched to BaseHeight, and everything else sits that much higher. */
    UPROPERTY(Category="Factory Demo|Appearance", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> BaseMesh;
    /** How high the platform lifts the building (cm); 0 leaves it on the floor. */
    UPROPERTY(Category="Factory Demo|Appearance", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float BaseHeight = 0;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) FVector MeshScale = FVector::OneVector;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) FVector MeshOffset = FVector::ZeroVector;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) float MeshYaw = 0;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) int32 ScrapCost = 10;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) int32 Capacity = 100;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) FName InputItem;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) FName OutputItem;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) int32 InputQuantity = 2;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) int32 OutputQuantity = 1;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) float CycleSeconds = 4;
    /** Belts only. 0: straight, from the back edge (-X) to the front edge (+X) of its cell. Otherwise a corner: from the
     *  back edge it bends this many degrees (negative: towards local -Y) along a 100 cm radius; -90 leaves by the side
     *  edge of the same cell. Mirror an actor (scale Y -1) to make it turn the other way. */
    UPROPERTY(Category="Factory Demo|Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="-180", ClampMax="180")) float TurnDegrees = 0;
};

UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryBuilding : public AActor
{
    GENERATED_BODY()
public:
    AFactoryBuilding();
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) TObjectPtr<UFactoryBuildingDefinition> Definition;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadWrite) FName PersistentId;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadWrite) int32 PaidScrap = 0;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadWrite) FName StorageItem = TEXT("Scrap");
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Visual;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Base;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UBoxComponent> Collision;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Cargo;
    /** Posts from a raised belt down to the floor (rebuilt when it moves). */
    UPROPERTY(Category="Factory Demo|Supports", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Supports;
    /** Post under a raised belt: stretched from the floor to the belt's underside (the actor's base). */
    UPROPERTY(Category="Factory Demo|Supports", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> SupportMesh;
    UPROPERTY(Category="Factory Demo|Supports", EditAnywhere, BlueprintReadOnly) TObjectPtr<UMaterialInterface> SupportMaterial;
    /** One post near each end and one every this many cm between them. */
    UPROPERTY(Category="Factory Demo|Supports", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="50")) float SupportSpacing = 250.0f;
    /** Post width (cm); 0 keeps SupportMesh's own width. */
    UPROPERTY(Category="Factory Demo|Supports", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float SupportWidth = 12.0f;
    /** Posts only where the belt is at least this high over the floor (cm). */
    UPROPERTY(Category="Factory Demo|Supports", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float SupportMinGap = 10.0f;
    UPROPERTY(Category="Factory Demo|Appearance", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UFactoryPresentationComponent> Presentation;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UFactoryInventoryComponent> Input;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UFactoryInventoryComponent> Output;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadWrite) float ProgressSeconds = 0;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) FString StateText;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) bool bConnected = false;
    UFUNCTION(Category="Factory Demo", BlueprintCallable) void RefreshVisuals();
    /** Height of the platform under this building (cm): its visuals, cargo and details are raised by this much. */
    UFUNCTION(Category="Factory Demo", BlueprintPure) float Lift() const;
    UFUNCTION(Category="Factory Demo", BlueprintPure) bool CanAccept(FName Item) const;
    UFUNCTION(Category="Factory Demo", BlueprintPure) UFactoryInventoryComponent* Supply() const;
    UFUNCTION(Category="Factory Demo", BlueprintPure) int32 StoredTotal() const;
    /** Belts: point of the path (local, unscaled) at Fraction 0..1 from the back edge, where cargo rides; OutYaw its heading. */
    FVector BeltLocalAt(float Fraction, float* OutYaw = nullptr) const;
    /** Belts: length of the path in the world (cm), with the actor's scale. */
    UFUNCTION(Category="Factory Demo", BlueprintPure) float BeltLength() const;
    /** Seconds an item takes to cross this belt (longer belts take longer). */
    UFUNCTION(Category="Factory Demo", BlueprintPure) float TravelSeconds() const;
    /** Where material comes in (the back edge) and goes out (the front edge, or a corner's side edge), in the world. */
    UFUNCTION(Category="Factory Demo", BlueprintPure) FVector InputPoint() const;
    UFUNCTION(Category="Factory Demo", BlueprintPure) FVector OutputPoint() const;
    /** Puts the cargo at Fraction 0..1 along the belt. */
    void PlaceCargo(float Fraction);
    /** Places the posts again (under a raised belt). */
    UFUNCTION(Category="Factory Demo", BlueprintCallable) void BuildSupports();
    void Simulate(float DeltaSeconds, AFactoryDemoWorld* Factory);
    void UpdateCargo(AFactoryDemoWorld* Factory);
    virtual void OnConstruction(const FTransform& Transform) override;
protected:
    virtual void BeginPlay() override;
};

USTRUCT()
struct FFactorySavedBuilding
{
    GENERATED_BODY()
    UPROPERTY() FName Id;
    UPROPERTY() FName DefinitionId;
    UPROPERTY() FVector Position = FVector::ZeroVector;
    UPROPERTY() float Yaw = 0;
    /** Version 3: full rotation (tilted belts) and scale (stretched belts). */
    UPROPERTY() FRotator Rotation = FRotator::ZeroRotator;
    UPROPERTY() FVector Scale = FVector::OneVector;
    UPROPERTY() int32 PaidScrap = 0;
    UPROPERTY() FName StorageItem = TEXT("Scrap");
    UPROPERTY() TMap<FName, int32> Input;
    UPROPERTY() TMap<FName, int32> Output;
    UPROPERTY() float ProgressSeconds = 0;
};

UCLASS()
class FACTORYCTYCORUNTIME_API UFactoryDemoSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() int32 Version = 3;
    UPROPERTY() TArray<FFactorySavedBuilding> Buildings;
    UPROPERTY() TMap<FName, int32> Piles;
    UPROPERTY() TMap<FName, int32> Inventory;
    UPROPERTY() FVector PlayerPosition = FVector::ZeroVector;
    UPROPERTY() int32 PlatesProduced = 0;
    UPROPERTY() int32 PlatesDelivered = 0;
    UPROPERTY() int32 SiteStage = 0;
    UPROPERTY() float SiteTransitionRemaining = 0;
};

UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryDemoWorld : public AActor
{
    GENERATED_BODY()
public:
    AFactoryDemoWorld();
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) TArray<TObjectPtr<UFactoryBuildingDefinition>> Catalog;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) TArray<TObjectPtr<UFactoryResourceDefinition>> Resources;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) TObjectPtr<UMaterialInterface> ValidMaterial;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) TObjectPtr<UMaterialInterface> InvalidMaterial;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) FVector2D AreaMin = FVector2D(-850, -750);
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) FVector2D AreaMax = FVector2D(850, 750);
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) float GridSize = 200;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadOnly) float FloorZ = 4;
    UPROPERTY(Category="Factory Demo", EditAnywhere, BlueprintReadWrite) FString SaveSlot = TEXT("FactoryCtycoDemo_v1");
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) int32 PlatesProduced = 0;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) int32 PlatesDelivered = 0;
    // Opt in per map so the separate GROW experiment keeps its own rules.
    UPROPERTY(Category="Factory Demo|Site", EditAnywhere, BlueprintReadOnly) bool bEnableSiteProgress = false;
    UPROPERTY(Category="Factory Demo|Site", EditAnywhere, BlueprintReadOnly) FVector2D ExpansionMin = FVector2D(-950, 1500);
    UPROPERTY(Category="Factory Demo|Site", EditAnywhere, BlueprintReadOnly) FVector2D ExpansionMax = FVector2D(950, 2350);
    UPROPERTY(Category="Factory Demo|Site", EditAnywhere, BlueprintReadOnly) FVector2D ConnectorMin = FVector2D(-100, 850);
    UPROPERTY(Category="Factory Demo|Site", EditAnywhere, BlueprintReadOnly) FVector2D ConnectorMax = FVector2D(100, 1500);
    UPROPERTY(Category="Factory Demo|Site", VisibleAnywhere, BlueprintReadOnly) int32 SiteStage = 0;
    UPROPERTY(Category="Factory Demo|Site", VisibleAnywhere, BlueprintReadOnly) float SiteTransitionRemaining = 0;
    UFUNCTION(Category="Factory Demo|Site", BlueprintPure) FString SiteStageName(int32 Stage) const;
    UFUNCTION(Category="Factory Demo|Site", BlueprintPure) int32 SiteNextTarget() const;
    UFUNCTION(Category="Factory Demo|Site", BlueprintPure) int32 SiteCurrentProgress() const;
    UFUNCTION(Category="Factory Demo", BlueprintPure) UFactoryResourceDefinition* Resource(FName Id) const;
    UFUNCTION(Category="Factory Demo", BlueprintPure) TArray<AFactoryBuilding*> Buildings() const;
    UFUNCTION(Category="Factory Demo", BlueprintPure) int32 StoredPlates() const;
    UFUNCTION(Category="Factory Demo", BlueprintPure) bool GoalComplete() const;
    UFUNCTION(Category="Factory Demo", BlueprintPure) FVector Snap(FVector Position) const;
    UFUNCTION(Category="Factory Demo", BlueprintCallable) FString PlacementProblem(FVector Position, const AActor* Ignore = nullptr) const;
    UFUNCTION(Category="Factory Demo", BlueprintCallable) bool SaveFactory(APawn* Player);
    UFUNCTION(Category="Factory Demo", BlueprintCallable) bool LoadFactory(APawn* Player);
    AFactoryBuilding* Receiver(const AFactoryBuilding* From, const TArray<AFactoryBuilding*>& All) const;
    float VisualSubstepSeconds() const { return FMath::Clamp(Accumulator, 0.0f, 0.1f); }
    virtual void Tick(float DeltaSeconds) override;
private:
    float Accumulator = 0;
    void Step(float DeltaSeconds);
    void StepSiteProgress(float DeltaSeconds);
};

UCLASS(ClassGroup=(Factory), meta=(BlueprintSpawnableComponent))
class FACTORYCTYCORUNTIME_API UFactoryDemoComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFactoryDemoComponent();
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<AFactoryDemoWorld> Factory;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<AFactoryBuilding> FocusedBuilding;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) bool bBuilding = false;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) int32 SelectedIndex = 0;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) int32 QuarterTurns = 0;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) FVector PreviewPosition = FVector::ZeroVector;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) bool bPreviewValid = false;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) FString PlacementMessage;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) FString Notification;
    UPROPERTY(Category="Factory Demo", VisibleAnywhere, BlueprintReadOnly) float NotificationUntil = 0;
    UFUNCTION(Category="Factory Demo", BlueprintCallable) void ToggleBuild();
    UFUNCTION(Category="Factory Demo", BlueprintCallable) void SelectBuilding(int32 Index);
    UFUNCTION(Category="Factory Demo", BlueprintCallable) void RotateBuilding();
    UFUNCTION(Category="Factory Demo", BlueprintCallable) void CancelBuild();
    UFUNCTION(Category="Factory Demo", BlueprintCallable) bool InteractMachine();
    UFUNCTION(Category="Factory Demo", BlueprintCallable) void Withdraw();
    UFUNCTION(Category="Factory Demo", BlueprintCallable) void CycleStorageItem();
    UFUNCTION(Category="Factory Demo", BlueprintCallable) bool Dismantle();
    UFUNCTION(Category="Factory Demo", BlueprintCallable) AFactoryBuilding* BuildAt(int32 Index, FVector Position, int32 Turns);
    UFUNCTION(Category="Factory Demo", BlueprintCallable) void RefreshFocus();
    UFUNCTION(Category="Factory Demo", BlueprintCallable) void Save();
    UFUNCTION(Category="Factory Demo", BlueprintCallable) void Load();
    UFUNCTION(Category="Factory Demo", BlueprintCallable, meta=(DevelopmentOnly)) bool SetEditorTestCursor(FVector WorldPosition);
    UFactoryInventoryComponent* Inventory() const;
    void Tell(const FString& Message);
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
private:
    UPROPERTY(Transient) TObjectPtr<UInputComponent> Controls;
    UPROPERTY(Transient) TObjectPtr<AActor> Preview;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> PreviewMesh;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> PreviewBase;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> PreviewPad;
    void UpdatePreview();
    void Click();
    /** Right drag orbits the camera; only a click without dragging cancels the build. */
    void RightRelease();
    void One(); void Two(); void Three(); void Four(); void Five();
    void DismantleKey();
};

UCLASS()
class FACTORYCTYCORUNTIME_API AFactoryDemoHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
    bool ClickCatalog(float X, float Y);
    /** A click on the info panel's options (key I); returns whether it hit one. */
    bool ClickInfoPanel(float X, float Y);
    /** Silences the whole game or brings the sound back (key M, or the option on the info panel). */
    UFUNCTION(BlueprintCallable, Category="HUD") void ToggleMute();
    UFUNCTION(BlueprintCallable, Category="HUD") bool IsMuted() const { return bMuted; }
    /** A click on the events sign (top left) opens or closes their detail; returns whether it hit it. */
    bool ClickEvents(float X, float Y);
    /** Opens or closes the events detail (what a click on the sign does). */
    UFUNCTION(BlueprintCallable, Category="HUD") void ToggleEvents() { bEventsOpen = !bEventsOpen; EventsOpenedAt = GetWorld()->GetRealTimeSeconds(); }
    /** Events on the sign right now. */
    UFUNCTION(BlueprintCallable, Category="HUD") int32 GetEventCount() const { return EventsSeen; }
    /** A click on a floor of the open elevator panel rides there; returns whether it hit one. */
    bool ClickElevator(float X, float Y);
    /** Opens the panel of a barrier booth (left click on it): its data and hire / upgrade. Null closes it. */
    UFUNCTION(BlueprintCallable, Category="HUD") void OpenBooth(class AFactoryGateBarrier* Barrier);
    /** A click on the booth panel's buttons; returns whether it hit the panel. */
    bool ClickBooth(float X, float Y);
    /** The booth whose panel is open, if any. */
    UFUNCTION(BlueprintCallable, Category="HUD") AActor* GetOpenBooth() const;
    /** Info panel page: 0 start, 1 hire staff. */
    UFUNCTION(BlueprintCallable, Category="HUD") void SetInfoTab(int32 Tab) { InfoTab = FMath::Clamp(Tab, 0, 1); InfoTabAt = GetWorld()->GetRealTimeSeconds(); }
    UFUNCTION(BlueprintCallable, Category="HUD") int32 GetInfoTab() const { return InfoTab; }
    /** Panels, hints and notices of the retired recycling demo (scrap, plates, objective). */
    UPROPERTY(EditAnywhere, Category="HUD") bool bShowRecyclingHUD = false;
private:
    TArray<FBox2D> CatalogButtons;
    /** Floor rows of the elevator panel, with their floor number. */
    TArray<TPair<FBox2D, int32>> ElevatorButtons;
    /** Info panel (key I): welcome message with the character's portrait, the objective and its progress,
     *  and options (for now, mute), "Pegatina Pop" look (Private/FactoryInfoPanel.cpp). */
    void DrawCharacterPanel(float S, float W, float H);
    /** Real time when the panel appeared or its look changed: its entrance plays from there. */
    float InfoShownAt = -100.0f;
    bool bInfoShown = false;
    int32 SeenDelivered = -1;
    float DeliveredAt = -100.0f, MutedAt = -100.0f;
    bool bMuted = false;
    /** Events sign (top left) and its detail. */
    void DrawEvents(float S, float W, float H);
    bool bEventsOpen = false;
    float EventsOpenedAt = -100.0f, EventsChangedAt = -100.0f;
    int32 EventsSeen = 0;
    FBox2D EventsBadge = FBox2D(ForceInit);
    /** "Mission complete" card, in the info panel's look. */
    void DrawMissionNotice(float S, float W, float H);
    FBox2D MuteButton = FBox2D(ForceInit);
    /** Info panel tabs (start, hire) and the hire button on the hire page. */
    int32 InfoTab = 0;
    float InfoTabAt = -100.0f;
    FBox2D TabButtons[2] = {FBox2D(ForceInit), FBox2D(ForceInit)};
    FBox2D HireButton = FBox2D(ForceInit);
    /** Booth panel (left click on the barrier booth): data, hire and upgrade. */
    void DrawBoothPanel(float S, float W, float H);
    TWeakObjectPtr<class AFactoryGateBarrier> OpenBoothActor;
    float BoothOpenedAt = -100.0f, UpgradeTriedAt = -100.0f;
    FBox2D BoothPanel = FBox2D(ForceInit), BoothHire = FBox2D(ForceInit), BoothUpgrade = FBox2D(ForceInit), BoothClose = FBox2D(ForceInit);
    /** The hire card, shared by the hire page and the booth panel: draws it at (X, Y) and returns its button. */
    FBox2D DrawHireCard(float S, float X, float Y, float CW, float Alpha, FVector2D Mouse);
    UPROPERTY(Transient) TObjectPtr<class UTexture2D> Portrait;
    /** Floors panel of the elevator the character is in (right side). */
    void DrawElevatorMenu(float S, float W, float H);
    /** Detail of the dispatch belt whose red sign was clicked (top right). */
    void DrawBeltDetail(float S, float W);
    /** The guide's story and briefing over the whole screen (and the cover fading after them); returns
     *  whether they cover the screen (nothing else is drawn then). Private/FactoryGuideHUD.cpp. */
    bool DrawGuideCover(float S, float W, float H);
    /** The current guide step's card (top left) and the screen-edge arrow to its target. */
    void DrawGuide(float S, float W, float H);
    /** The factory's money (top left) with "+$60" / "-$800" pops when it changes, and the mute button next to it
     *  (always visible). */
    void DrawMoney(float S, float W, float H);
    FBox2D MuteCorner = FBox2D(ForceInit);
public:
    /** A click on the mute button next to the money; returns whether it hit it. */
    bool ClickMoneyBar(float X, float Y);
private:
    /** Speech bubbles of the characters who are talking (AFactoryNpc), over their heads. */
    void DrawNpcSpeech(float S, float W, float H);
    /** Elevator floor the current guide step asks for (highlighted on the elevator panel), or empty. */
    FString GuideElevatorStop() const;
};
