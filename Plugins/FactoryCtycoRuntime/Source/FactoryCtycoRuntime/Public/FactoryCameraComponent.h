#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FactoryCameraComponent.generated.h"

class USpringArmComponent;
class UInputComponent;
class APlayerController;
class ACharacter;

/**
 * Mouse camera controls with pan, zoom, and orbit at a fixed isometric pitch.
 * With bStartFree the camera does not ride on its pawn: it stays where it is (middle drag pans it, with no
 * limit) until a character is picked (FollowAtScreen / Follow), which it then follows; panning or
 * StopFollowing frees it again, Home follows the own pawn. When the own pawn jumps far in one frame (an
 * elevator ride), a free camera jumps along with it.
 */
UCLASS(ClassGroup=(Factory), meta=(BlueprintSpawnableComponent))
class FACTORYCTYCORUNTIME_API UFactoryCameraComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFactoryCameraComponent();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Factory Camera", meta=(ClampMin="100"))
    float MinimumDistance = 1100.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Factory Camera", meta=(ClampMin="100"))
    float MaximumDistance = 9000.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Factory Camera", meta=(ClampMin="0.01", ClampMax="0.5"))
    float ZoomFraction = 0.1f;
    // Mouse axes retain the project's 0.07 sensitivity; this gives a natural drag speed.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Factory Camera", meta=(ClampMin="0.1"))
    float PanSensitivity = 18.0f;
    // Degrees per processed mouse-axis unit (the project uses 0.07 sensitivity).
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Factory Camera", meta=(ClampMin="0.1"))
    float OrbitSensitivity = 3.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Factory Camera", meta=(ClampMin="0"))
    float MaximumPanDistance = 1250.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Factory Camera", meta=(ClampMin="0.1"))
    float SmoothingSpeed = 10.0f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Factory Camera")
    float DesiredDistance = 2450.0f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Factory Camera")
    FVector DesiredPan = FVector::ZeroVector;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Factory Camera")
    float DesiredYaw = -45.0f;
    /** Free camera from the start (does not follow the pawn until a character is clicked). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Factory Camera")
    bool bStartFree = false;
    /** Arrow keys slide the camera (cm per second at the starting zoom; more when zoomed out). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Factory Camera", meta=(ClampMin="0"))
    float KeyPanSpeed = 1400.0f;
    /** Pixels around a character's body on screen that count as clicking on it. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Factory Camera", meta=(ClampMin="5"))
    float PickRadius = 45.0f;

    /** Follows Target (a character; one hidden in a car is followed through its car). */
    UFUNCTION(BlueprintCallable, Category="Factory Camera")
    void Follow(AActor* Target);
    /** Leaves the camera free where it is. */
    UFUNCTION(BlueprintCallable, Category="Factory Camera")
    void StopFollowing();
    /** Follows the character drawn at this screen position, if any; returns whether one was picked. */
    UFUNCTION(BlueprintCallable, Category="Factory Camera")
    bool FollowAtScreen(FVector2D ScreenPosition);
    /** The character drawn at this screen position (what a click would follow), if any. */
    UFUNCTION(BlueprintCallable, Category="Factory Camera")
    ACharacter* CharacterAtScreen(FVector2D ScreenPosition) const;
    UFUNCTION(BlueprintCallable, Category="Factory Camera")
    AActor* GetFollowTarget() const { return FollowTarget.Get(); }
    UFUNCTION(BlueprintCallable, Category="Factory Camera")
    bool IsFree() const { return bFree; }
    /** Where the camera looks (world). */
    UFUNCTION(BlueprintCallable, Category="Factory Camera")
    FVector GetFocus() const { return Focus; }

    UFUNCTION(BlueprintCallable, Category="Factory Camera")
    void ResetCamera();

    /** First person: the camera goes to the character's eyes (its body hides) and the mouse looks around (the cursor
     *  hides and stays in the window); WASD walks where it looks. Off: back to the isometric camera as it was, with the
     *  cursor. Key V or the button next to mute. */
    UFUNCTION(BlueprintCallable, Category="Factory Camera")
    void SetFirstPerson(bool bOn);
    UFUNCTION(BlueprintCallable, Category="Factory Camera")
    void ToggleFirstPerson() { SetFirstPerson(!bFirstPerson); }
    UFUNCTION(BlueprintCallable, Category="Factory Camera")
    bool IsFirstPerson() const { return bFirstPerson; }
    /** Eyes over the character's middle (its capsule centre), cm. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Factory Camera|First Person")
    float EyeHeight = 65.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Factory Camera|First Person", meta=(ClampMin="30", ClampMax="120"))
    float FirstPersonFov = 85.0f;
    /** First person: degrees the view turns per processed mouse-axis unit. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Factory Camera|First Person", meta=(ClampMin="0.1"))
    float LookSensitivity = 2.0f;
    /** Mouse movement since the right button went down; a right drag orbits instead of clicking. */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Factory Camera")
    float RightDragSincePress = 0.0f;
    // Editor automation sends events through PlayerController and the real input stack.
    // This helper does nothing in a packaged game.
    UFUNCTION(BlueprintCallable, Category="Factory Camera|Testing", meta=(DevelopmentOnly))
    bool SendEditorTestInput(FName KeyName, float Value = 1.0f, bool bPressed = true);
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
private:
    void BindControls(APlayerController* Player);
    void ZoomIn();
    void StartRightDrag();
    void ZoomOut();
    void PanHorizontal(float Value);
    void PanVertical(float Value);
    void Pan(float Horizontal, float Vertical);
    /** Arrow keys held down: slides the view (a free camera lets go of the character it follows). */
    void KeyPan(float DeltaTime);
    bool IsOrbiting() const;
    TWeakObjectPtr<USpringArmComponent> SpringArm;
    TWeakObjectPtr<APlayerController> Controller;
    UPROPERTY(Transient)
    TObjectPtr<UInputComponent> CameraInput;
    float InitialDistance = 2450.0f;
    FVector InitialOffset = FVector::ZeroVector;
    FRotator InitialRotation = FRotator::ZeroRotator;
    /** Free camera: the arm is placed in the world at Focus (+ its offset over the pawn) instead of riding along. */
    bool bFree = false;
    bool bFirstPerson = false;
    /** First person: looking up (+) or down (-), degrees. */
    float LookPitch = 0.0f;
    /** The arm's place on the pawn and the camera's field of view, to put back after first person. */
    FVector ArmRelative = FVector::ZeroVector;
    float IsometricFov = 90.0f;
    bool bWasFree = false;
    bool bArmCollided = false;
    FVector ArmSocket = FVector::ZeroVector;
    TWeakObjectPtr<AActor> FollowTarget;
    FVector Focus = FVector::ZeroVector;
    FVector ArmOverPawn = FVector::ZeroVector;
    FVector LastPawnLocation = FVector::ZeroVector;
    /** Where Target is (its car while it drives); false when it cannot be seen. */
    static bool TargetLocation(const AActor* Target, FVector& Out);
};
