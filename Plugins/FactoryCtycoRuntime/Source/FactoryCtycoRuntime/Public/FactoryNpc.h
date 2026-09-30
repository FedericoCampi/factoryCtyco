#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryNpc.generated.h"

class UAnimationAsset;
class UBoxComponent;
class USkeletalMeshComponent;
class USoundBase;
class UStaticMeshComponent;

/**
 * A character of the scenery who talks when the player comes close: a speech bubble over the head shows
 * Lines one after the other (the HUD draws it, Private/FactoryGuideHUD.cpp), each with its voice clip from
 * LineSounds, and goes away when the player leaves. The body is a skeletal mesh looping IdleAnimation (e.g. the
 * seated vagabond breathing and looking around) or, without one, a static mesh that breathes a little.
 * Blocker keeps the player from walking through.
 */
UCLASS()
class FACTORYCTYCORUNTIME_API AFactoryNpc : public AActor
{
    GENERATED_BODY()
public:
    AFactoryNpc();
    UPROPERTY(Category="NPC", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneComponent> Root;
    UPROPERTY(Category="NPC", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USkeletalMeshComponent> Skeletal;
    UPROPERTY(Category="NPC", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Body;
    UPROPERTY(Category="NPC", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UBoxComponent> Blocker;
    /** Loops on Skeletal while playing. */
    UPROPERTY(Category="NPC", EditAnywhere, BlueprintReadWrite) TObjectPtr<UAnimationAsset> IdleAnimation;
    /** Played once when a line is said (e.g. raising an arm); then back to IdleAnimation. */
    UPROPERTY(Category="NPC", EditAnywhere, BlueprintReadWrite) TObjectPtr<UAnimationAsset> TalkAnimation;
    /** Name on the bubble's tag. */
    UPROPERTY(Category="NPC", EditAnywhere, BlueprintReadWrite) FString DisplayName = TEXT("Vagabundo");
    /** What the character says, in order (the last one stays while the player is near). */
    UPROPERTY(Category="NPC", EditAnywhere, BlueprintReadWrite) TArray<FString> Lines;
    /** The voice of each line (same order as Lines; missing ones are silent). */
    UPROPERTY(Category="NPC", EditAnywhere, BlueprintReadWrite) TArray<TObjectPtr<USoundBase>> LineSounds;
    /** How close the player must be for the character to speak (cm). */
    UPROPERTY(Category="NPC", EditAnywhere, BlueprintReadWrite, meta=(ClampMin="50")) float TalkRadius = 280.0f;
    /** Height of the bubble's tip over the actor's origin (cm). */
    UPROPERTY(Category="NPC", EditAnywhere, BlueprintReadWrite) float SpeechHeight = 135.0f;
    UPROPERTY(Category="NPC", EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0.5")) float SecondsPerLine = 3.5f;

    /** Whether the bubble is up (or still fading out). */
    UFUNCTION(BlueprintCallable, Category="NPC") bool IsTalking() const { return bTalking; }
    /** The line on the bubble now. */
    UFUNCTION(BlueprintCallable, Category="NPC") FString GetLine() const { return Lines.IsValidIndex(Line) ? Lines[Line] : FString(); }
    /** Whether TalkAnimation is playing now. */
    UFUNCTION(BlueprintCallable, Category="NPC") bool IsGesturing() const { return TalkEndsAt > 0.0f; }
    /** How many lines have been voiced since play began. */
    UFUNCTION(BlueprintCallable, Category="NPC") int32 GetLinesVoiced() const { return LinesVoiced; }
    /** Real time when the current line appeared, and when the player walked away (the bubble fades from there). */
    float GetLineShownAt() const { return LineShownAt; }
    float GetLeftAt() const { return LeftAt; }
    bool IsNear() const { return bNear; }
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
private:
    FVector BaseScale = FVector::OneVector;
    bool bNear = false, bTalking = false;
    int32 Line = 0, LinesVoiced = 0;
    float LineShownAt = -100.0f, LeftAt = -100.0f;
    /** Real time when TalkAnimation ends (0: not playing). */
    float TalkEndsAt = 0.0f;
    void SayLine(int32 Index, float Now);
};
