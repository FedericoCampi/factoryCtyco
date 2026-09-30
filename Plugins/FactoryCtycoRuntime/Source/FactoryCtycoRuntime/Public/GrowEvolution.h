#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/HUD.h"
#include "GrowEvolution.generated.h"

class UStaticMesh;
class USkeletalMesh;
class UAnimSequence;
class UStaticMeshComponent;
class USkeletalMeshComponent;
class UMaterialInterface;
class USpringArmComponent;
class UCameraComponent;
class UFactoryCameraComponent;
class AGrowEvolutionWorld;

UENUM(BlueprintType)
enum class EGrowDecision : uint8 { Recycling, Water, Logistics, Energy, Habitat, Awaken };

UENUM(BlueprintType)
enum class EGrowProfession : uint8 { Apprentice, Builder, Caretaker, Courier };

/** Species appearance is independent from the turn/role rules: more creatures can share the simulation. */
UCLASS(BlueprintType)
class FACTORYCTYCORUNTIME_API UGrowSpeciesDefinition : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grow") FName SpeciesId = TEXT("Robot");
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grow") FText DisplayName;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<USkeletalMesh> BodyMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<UAnimSequence> IdleAnimation;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<UAnimSequence> WalkAnimation;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grow") FVector BodyScale = FVector(.70f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grow") FRotator BodyRotation = FRotator(0,-90,0);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grow") FVector AccessoryOffset = FVector(-20,0,82);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grow") TMap<EGrowProfession,TObjectPtr<UStaticMesh>> ProfessionMeshes;
};

UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AGrowCreature : public AActor
{
    GENERATED_BODY()
public:
    AGrowCreature();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<USkeletalMeshComponent> Body;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<UStaticMeshComponent> Accessory;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<UStaticMeshComponent> Cargo;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<UGrowSpeciesDefinition> Species;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") EGrowProfession Profession = EGrowProfession::Apprentice;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") int32 Level = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") float MotionPhase = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") FString Activity;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") EGrowDecision WorkSource = EGrowDecision::Awaken;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") EGrowDecision WorkTarget = EGrowDecision::Awaken;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") bool bDelivering = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") int32 CompletedTrips = 0;
    void Configure(AGrowEvolutionWorld* InWorld, int32 Index);
    void ApplyEvolution();
    virtual void Tick(float DeltaSeconds) override;
private:
    UPROPERTY(Transient) TObjectPtr<AGrowEvolutionWorld> Evolution;
    int32 ColonyIndex = 0;
    bool bWalking = false;
    int32 JobStage = 0;
    float WorkPause = 0;
    FVector WorkGoal = FVector::ZeroVector;
};

USTRUCT()
struct FGrowWorldPiece
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Mesh;
    EGrowDecision Decision = EGrowDecision::Awaken;
    int32 RequiredLevel = 0;
    int32 RequiredCreatureLevel = 0;
    EGrowProfession RequiredProfession = EGrowProfession::Apprentice;
    FVector Scale = FVector::OneVector;
    FRotator Rotation = FRotator::ZeroRotator;
    float Spin = 0;
    float Reveal = 0;
};

USTRUCT(BlueprintType)
struct FGrowInteraction
{
    GENERATED_BODY()
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") EGrowDecision Source = EGrowDecision::Energy;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") EGrowDecision Target = EGrowDecision::Recycling;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") int32 RequiredLevel = 1;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") bool bActive = false;
};

USTRUCT(BlueprintType)
struct FGrowUpgrade
{
    GENERATED_BODY()
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") EGrowDecision Source = EGrowDecision::Energy;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") EGrowDecision Target = EGrowDecision::Recycling;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") int32 Level = 2;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") FString Reason;
};

USTRUCT()
struct FGrowConnectionVisual
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Path;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Pulse;
    EGrowDecision Source = EGrowDecision::Energy;
    EGrowDecision Target = EGrowDecision::Recycling;
};

UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AGrowEvolutionWorld : public AActor
{
    GENERATED_BODY()
public:
    AGrowEvolutionWorld();
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<UGrowSpeciesDefinition> Species;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<UStaticMesh> BoxMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<UStaticMesh> CylinderMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<UStaticMesh> BeltMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<UMaterialInterface> DetailMaterial;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") TArray<EGrowDecision> History;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") TArray<int32> SystemLevels;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") EGrowProfession Profession = EGrowProfession::Apprentice;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") int32 CreatureLevel = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") TArray<TObjectPtr<AGrowCreature>> Creatures;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") float TransitionRemaining = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") FString LastEvent;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") int32 VisiblePieceCount = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") float MotionPhase = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Grow|Timing", meta=(ClampMin="0.1", ClampMax="10")) float UpgradeDelaySeconds = 2.0f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow|Interactions") bool bResolving = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow|Interactions") float EvolutionCountdown = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow|Interactions") int32 PendingUpgradeCount = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow|Interactions") EGrowDecision PendingDecision = EGrowDecision::Energy;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow|Interactions") EGrowDecision PendingSource = EGrowDecision::Energy;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow|Interactions") FString PendingReason;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow|Interactions") int32 ActiveLinks = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow|Interactions") int32 UpgradeSerial = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow|Interactions") FGrowUpgrade LastUpgrade;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow|Interactions") TArray<FGrowInteraction> Interactions;
    UFUNCTION(BlueprintPure, Category="Grow") FString SystemHint(EGrowDecision Decision) const;
    UFUNCTION(BlueprintCallable, Category="Grow") bool ChooseDecision(EGrowDecision Decision);
    UFUNCTION(BlueprintCallable, Category="Grow") bool UndoDecision();
    UFUNCTION(BlueprintCallable, Category="Grow") void ResetEvolution();
    UFUNCTION(BlueprintPure, Category="Grow") bool HasDecision(EGrowDecision Decision) const;
    UFUNCTION(BlueprintPure, Category="Grow") int32 DecisionLevel(EGrowDecision Decision) const;
    UFUNCTION(BlueprintPure, Category="Grow") bool IsComplete() const;
    UFUNCTION(BlueprintPure, Category="Grow") bool IsSuccessful() const;
    UFUNCTION(BlueprintPure, Category="Grow") FString ProgressHint() const;
    UFUNCTION(BlueprintPure, Category="Grow") FString OutcomeText() const;
    UFUNCTION(BlueprintPure, Category="Grow") FString PreviewProfession() const;
    UFUNCTION(BlueprintPure, Category="Grow") static FString DecisionName(EGrowDecision Decision);
    UFUNCTION(BlueprintPure, Category="Grow") static FString DecisionDescription(EGrowDecision Decision);
    UFUNCTION(BlueprintPure, Category="Grow") static FString ProfessionName(EGrowProfession Value);
    UFUNCTION(BlueprintPure, Category="Grow") static FLinearColor DecisionColor(EGrowDecision Decision);
    UFUNCTION(BlueprintPure, Category="Grow") static FLinearColor ProfessionColor(EGrowProfession Value);
    static FVector Station(EGrowDecision Decision);
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
private:
    UPROPERTY(Transient) TArray<FGrowWorldPiece> Pieces;
    UPROPERTY(Transient) TArray<FGrowUpgrade> PendingUpgrades;
    UPROPERTY(Transient) TArray<FGrowConnectionVisual> ConnectionVisuals;
    float ActiveUpgradeDuration = 2;
    void Recompute();
    void BuildUpgradePlan();
    void StartNextUpgrade();
    void ApplyNextUpgrade();
    void CancelUpgrades();
    void RefreshInteractions();
    void BuildConnections();
    void UpdateConnections(float DeltaSeconds);
    void BuildPresentation();
    void UpdateCreatures();
    void AddPiece(const FString& Name, EGrowDecision Decision, int32 Level, FVector Position, FVector Scale,
        FLinearColor Color, bool bCylinder=false, float Spin=0, int32 RequiredCreatureLevel=0,
        EGrowProfession RequiredProfession=EGrowProfession::Apprentice, UStaticMesh* OverrideMesh=nullptr);
};

UCLASS()
class FACTORYCTYCORUNTIME_API AGrowViewPawn : public APawn
{
    GENERATED_BODY()
public:
    AGrowViewPawn();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<USpringArmComponent> SpringArm;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grow") TObjectPtr<UFactoryCameraComponent> CameraControls;
};

UCLASS()
class FACTORYCTYCORUNTIME_API AGrowPlayerController : public APlayerController
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintPure, Category="Grow") AGrowEvolutionWorld* Evolution() const;
protected:
    virtual void BeginPlay() override;
    virtual void SetupInputComponent() override;
private:
    void Choose0(); void Choose1(); void Choose2(); void Choose3(); void Choose4(); void Choose5();
    void Undo(); void Restart(); void Click();
};

UCLASS()
class FACTORYCTYCORUNTIME_API AGrowEvolutionHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
    bool Click(float X, float Y);
private:
    TArray<FBox2D> DecisionButtons;
    FBox2D UndoButton;
    FBox2D ResetButton;
};

UCLASS()
class FACTORYCTYCORUNTIME_API AGrowEvolutionGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AGrowEvolutionGameMode();
};
