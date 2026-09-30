#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryGuide.generated.h"

class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class UInputComponent;

/** When a guide step counts as done. */
UENUM(BlueprintType)
enum class EFactoryGuideGoal : uint8
{
    /** The character gets within Radius of GoalActor (an elevator must also have finished its trip). */
    Reach,
    /** The dispatch belt GoalActor is switched on (any dispatch belt when GoalActor is empty). */
    SwitchOnBelt,
    /** The character holds a box. */
    CarryBox,
    /** A box is on a loading belt or already in a truck. */
    LoadBox,
    /** The mission's delivery goal is reached. */
    Deliver,
    /** The truck gate GoalActor (a roll door or a barrier) is open and lets trucks through. */
    OpenGate,
};

/** One step of the path to the mission, shown on the objective card with the big arrow on its target. */
USTRUCT(BlueprintType)
struct FFactoryGuideStep
{
    GENERATED_BODY()
    /** What to do, short (the card's main line). */
    UPROPERTY(Category="Guide", EditAnywhere, BlueprintReadWrite) FString Title;
    /** How to do it (the card's second line). */
    UPROPERTY(Category="Guide", EditAnywhere, BlueprintReadWrite) FString Hint;
    /** Where the big arrow points; none hides the arrow. */
    UPROPERTY(Category="Guide", EditAnywhere, BlueprintReadWrite) TObjectPtr<AActor> ArrowTarget;
    UPROPERTY(Category="Guide", EditAnywhere, BlueprintReadWrite) EFactoryGuideGoal Goal = EFactoryGuideGoal::Reach;
    /** Actor the goal is about (Reach: where to arrive; SwitchOnBelt: the belt). Empty: ArrowTarget. */
    UPROPERTY(Category="Guide", EditAnywhere, BlueprintReadWrite) TObjectPtr<AActor> GoalActor;
    /** Reach: how close counts as arrived (cm). */
    UPROPERTY(Category="Guide", EditAnywhere, BlueprintReadWrite, meta=(ClampMin="50")) float Radius = 450.0f;
    /** Elevator floor (StopName) to highlight on the elevator panel during this step. */
    UPROPERTY(Category="Guide", EditAnywhere, BlueprintReadWrite) FString ElevatorStop;
};

/** One card of the story shown when the game starts. */
USTRUCT(BlueprintType)
struct FFactoryIntroSlide
{
    GENERATED_BODY()
    /** Small line above the title (a date, a place...). */
    UPROPERTY(Category="Guide", EditAnywhere, BlueprintReadWrite) FString Kicker;
    UPROPERTY(Category="Guide", EditAnywhere, BlueprintReadWrite) FString Title;
    /** Body text; each line break is a line on the card. */
    UPROPERTY(Category="Guide", EditAnywhere, BlueprintReadWrite, meta=(MultiLine="true")) FString Body;
};

/**
 * The start of the game: an intro (story cards over the darkened factory), then the first mission's
 * briefing, then its steps one by one. The current step shows on the objective card (top left) and a big
 * bouncing arrow floats over its target; when the target is off screen an arrow at the screen edge points
 * to it. Place one in the level ("Guia_Mision") and fill Steps with actors of the level.
 * Space, Enter or a click moves the intro on; the rest of the game's input waits meanwhile.
 * The HUD (AFactoryDemoHUD) draws it all (Private/FactoryGuideHUD.cpp).
 */
UCLASS()
class FACTORYCTYCORUNTIME_API AFactoryGuide : public AActor
{
    GENERATED_BODY()
public:
    AFactoryGuide();

    enum class EPhase : uint8 { Intro, Briefing, Steps, Done };

    UPROPERTY(Category="Guide|Intro", EditAnywhere, BlueprintReadWrite) TArray<FFactoryIntroSlide> Slides;
    /** Skips the intro and briefing (handy for testing): the steps start at once. */
    UPROPERTY(Category="Guide|Intro", EditAnywhere, BlueprintReadWrite) bool bSkipIntro = false;

    UPROPERTY(Category="Guide|Mission", EditAnywhere, BlueprintReadWrite) FString MissionKicker = TEXT("MISIÓN 1");
    UPROPERTY(Category="Guide|Mission", EditAnywhere, BlueprintReadWrite) FString MissionTitle = TEXT("Reabrir el despacho");
    UPROPERTY(Category="Guide|Mission", EditAnywhere, BlueprintReadWrite, meta=(MultiLine="true")) FString MissionBody;
    UPROPERTY(Category="Guide|Mission", EditAnywhere, BlueprintReadWrite) TArray<FFactoryGuideStep> Steps;

    /** Height of the arrow's tip over the target's top (cm). */
    UPROPERTY(Category="Guide|Arrow", EditAnywhere, BlueprintReadWrite) float ArrowHeight = 90.0f;
    /** Arrow size (1 = 2.6 m tall). */
    UPROPERTY(Category="Guide|Arrow", EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0.1")) float ArrowScale = 1.0f;
    UPROPERTY(Category="Guide|Arrow", EditAnywhere, BlueprintReadWrite) FLinearColor ArrowColor = FLinearColor(1.0f, .42f, .04f, 1.0f);

    /** The guide of World, if the level has one. */
    static AFactoryGuide* Find(const UWorld* World);

    EPhase GetPhase() const { return Phase; }
    /** Intro card on screen (Slides.Num() is the briefing). */
    int32 GetSlide() const { return Slide; }
    /** Real time when the current card, step or phase appeared. */
    float GetShownAt() const { return ShownAt; }
    /** Whether the story or briefing covers the screen (the HUD hides everything else). */
    bool IsCovering() const { return Phase == EPhase::Intro || Phase == EPhase::Briefing; }
    /** Real time when the intro ended (the cover fades out from there). */
    float GetIntroEndedAt() const { return IntroEndedAt; }
    UFUNCTION(BlueprintCallable, Category="Guide") int32 GetStepIndex() const { return Step; }
    const FFactoryGuideStep* GetStep() const { return Phase == EPhase::Steps && Steps.IsValidIndex(Step) ? &Steps[Step] : nullptr; }
    /** Real time when the last step was completed (the card shows a tick for a moment). */
    float GetStepDoneAt() const { return StepDoneAt; }
    /** World point the arrow's tip is on; false when the current step has no arrow. */
    bool GetArrowPoint(FVector& Out) const;

    /** Moves the intro to the next card (or starts the mission after the briefing). */
    UFUNCTION(BlueprintCallable, Category="Guide") void Advance();
    /** Jumps to the steps (skipping the rest of the intro). */
    UFUNCTION(BlueprintCallable, Category="Guide") void SkipIntro();

    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Category="Guide", VisibleAnywhere) TObjectPtr<USceneComponent> Root;
    UPROPERTY(Category="Guide", VisibleAnywhere) TObjectPtr<USceneComponent> Arrow;
    UPROPERTY(Category="Guide", VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Shaft;
    UPROPERTY(Category="Guide", VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Head;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ArrowMaterial;
    UPROPERTY(Transient) TObjectPtr<UInputComponent> IntroInput;

    EPhase Phase = EPhase::Intro;
    int32 Slide = 0;
    int32 Step = 0;
    float ShownAt = 0.0f;
    float IntroEndedAt = -100.0f;
    float StepDoneAt = -100.0f;
    /** A completed step waits this long (showing its tick) before the next one appears. */
    bool bStepPending = false;

    void StartSteps();
    void EndIntroInput();
    bool IsStepDone(const FFactoryGuideStep& S) const;
    void UpdateArrow(float Now);
};
