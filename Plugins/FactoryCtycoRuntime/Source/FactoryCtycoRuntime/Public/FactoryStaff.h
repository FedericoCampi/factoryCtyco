#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Character.h"
#include "Subsystems/WorldSubsystem.h"
#include "FactoryStaff.generated.h"

class AFactoryElevator;
class AFactoryGateBarrier;
class AStaticMeshActor;
class UStaticMesh;
class USplineComponent;
class UTextRenderComponent;
class URobotLocomotionComponent;

/** What a hired worker is doing. */
UENUM(BlueprintType)
enum class EFactoryWorkerState : uint8
{
    Driving,   // arriving by car along the hire point's CarRoute
    Walking,   // on foot, to the elevator or to the workplace
    Riding,    // in the elevator, between floors
    Working,   // at the workplace, waiting for something to do
    Acting     // doing it (e.g. raising the barrier)
};

/**
 * Where hired workers arrive: they drive in along CarRoute (first point: where the car appears; last point:
 * the parking space, the car's nose pointing along the line) in one of CarMeshes, park, get out and walk
 * (navigation mesh) to the elevator of that floor, ride to the workplace's floor and walk to the workplace.
 * Job says which job it serves ("Barrera": the barrier attendant); Workplace: the barrier it works (empty:
 * the nearest one). Without CarRoute points or car meshes the worker appears at the actor on foot.
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryWorkerSpawn : public AActor
{
    GENERATED_BODY()
public:
    AFactoryWorkerSpawn();
    UPROPERTY(Category="Staff", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USplineComponent> CarRoute;
    UPROPERTY(Category="Staff", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> Label;
    UPROPERTY(Category="Staff", EditAnywhere, BlueprintReadOnly) FName Job = TEXT("Barrera");
    UPROPERTY(Category="Staff", EditInstanceOnly, BlueprintReadOnly) TObjectPtr<AFactoryGateBarrier> Workplace;
    /** Cars they may come in (one is picked at random). */
    UPROPERTY(Category="Staff", EditAnywhere, BlueprintReadOnly) TArray<TObjectPtr<UStaticMesh>> CarMeshes;
    /** cm per second; it slows down over the last metres into the space. */
    UPROPERTY(Category="Staff", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="50")) float CarSpeed = 550.0f;
    /** The barrier it works: Workplace, or the nearest one. */
    AFactoryGateBarrier* FindWorkplace() const;
};

/**
 * A hired worker: a copy of the player's character (same mesh, animation and walking speed, taken from the
 * player's pawn when it appears). It arrives by car at its hire point, walks to the elevator, rides to the
 * workplace's floor and walks there (paths from the navigation mesh), then works: the barrier attendant
 * raises the barrier a moment after a truck stops at it (the barrier comes down by itself once through).
 */
UCLASS()
class FACTORYCTYCORUNTIME_API AFactoryWorker : public ACharacter
{
    GENERATED_BODY()
public:
    AFactoryWorker();
    UPROPERTY(Category="Staff", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<URobotLocomotionComponent> Locomotion;
    UPROPERTY(Category="Staff", VisibleInstanceOnly, BlueprintReadOnly) FName Job;
    UPROPERTY(Category="Staff", VisibleInstanceOnly, BlueprintReadOnly) TObjectPtr<AFactoryWorkerSpawn> Spawn;
    UPROPERTY(Category="Staff", VisibleInstanceOnly, BlueprintReadOnly) TObjectPtr<AFactoryGateBarrier> Workplace;
    /** Its car, which stays parked where it left it. */
    UPROPERTY(Category="Staff", VisibleInstanceOnly, BlueprintReadOnly) TObjectPtr<AStaticMeshActor> Car;
    UPROPERTY(Category="Staff", VisibleInstanceOnly, BlueprintReadOnly) EFactoryWorkerState State = EFactoryWorkerState::Walking;
    /** Seconds from a truck stopping at the barrier until the attendant raises it. */
    UPROPERTY(Category="Staff", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float ReactionSeconds = 0.8f;
    /** Seconds it spends in the elevator between floors. */
    UPROPERTY(Category="Staff", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float RideSeconds = 3.0f;
    /** Times it was held back and slipped ahead to its next point (0 when the paths are clear). */
    UPROPERTY(Category="Staff", VisibleInstanceOnly, BlueprintReadOnly) int32 Skips = 0;
    /** Where it was held back the last time (to fix that spot). */
    UPROPERTY(Category="Staff", VisibleInstanceOnly, BlueprintReadOnly) FVector LastHeldAt = FVector::ZeroVector;
    /** Trucks it let through. */
    UPROPERTY(Category="Staff", VisibleInstanceOnly, BlueprintReadOnly) int32 Handled = 0;
    UFUNCTION(BlueprintCallable, Category="Staff") EFactoryWorkerState GetState() const { return State; }
    /** Whether it is still on its way (car, elevator or walking to the workplace). */
    UFUNCTION(BlueprintCallable, Category="Staff") bool IsOnTheWay() const { return State == EFactoryWorkerState::Driving || State == EFactoryWorkerState::Walking || State == EFactoryWorkerState::Riding; }
    /** What it is doing, for the panels. */
    FString Describe() const;
    /** Takes the look of Source (the player's character): mesh, animations, speeds, capsule. */
    void CopyLook(const ACharacter* Source);
    /** Starts the trip: by car when the hire point has a car route, else on foot from where it stands. */
    void Begin();
    virtual void Tick(float DeltaSeconds) override;
private:
    /** Points still to walk to, in order. */
    TArray<FVector> Path;
    bool bSecondLeg = false;      // walking from the arrival elevator to the workplace
    float CarAlong = 0.0f;
    float RideLeft = 0.0f;
    float Stuck = 0.0f, BestGap = 0.0f;
    /** Whether the way to the current point was already searched again after getting held back. */
    bool bReplanned = false;
    float WaitingFor = 0.0f;      // seconds a truck has been waiting at the barrier
    TWeakObjectPtr<AFactoryElevator> FromElevator, ToElevator;
    /** On foot from here: to this floor's elevator (if the workplace is on another floor) or to the workplace. */
    void StartWalking();
    void Drive(float DeltaSeconds);
    void Walk(float DeltaSeconds);
    void Ride(float DeltaSeconds);
    void Work(float DeltaSeconds);
    /** Shows it on foot at Where (or hides it, in the car or the elevator). */
    void SetOnFoot(bool bOnFoot);
    /** Path from here to Goal over the navigation mesh (straight when there is none), then Extra. */
    void PlanTo(const FVector& Goal, const TArray<FVector>& Extra = {});
    /** Where the work is done: inside the booth. */
    FVector WorkSpot() const;
    /** Just outside the booth's door (its -X side): the walk goes there, then straight in. */
    FVector WorkDoor() const;
    /** Appends the way from From to the workplace: navigation to its door, then inside. */
    void AddWorkLeg(const FVector& From);
    /** Just outside an elevator's doors. */
    static FVector ElevatorFront(const AFactoryElevator* Elevator);
    AFactoryElevator* NearestElevator(const FVector& Where) const;
    void ArriveAtWork();
};

/** Who is hired. Hire(Role) brings a worker from that role's hire point. */
UCLASS()
class FACTORYCTYCORUNTIME_API UFactoryStaffSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintPure, Category="Staff", meta=(WorldContext="Context")) static UFactoryStaffSubsystem* Get(const UObject* Context);
    UFUNCTION(BlueprintCallable, Category="Staff") bool IsHired(FName Role) const;
    UFUNCTION(BlueprintCallable, Category="Staff") AFactoryWorker* GetWorker(FName Role) const;
    /** Whether a worker can be hired for Role (there is a hire point for it and nobody has the job yet). */
    UFUNCTION(BlueprintCallable, Category="Staff") bool CanHire(FName Role) const;
    /** Brings a worker for Role from its hire point; returns it (null if it cannot). */
    UFUNCTION(BlueprintCallable, Category="Staff") AFactoryWorker* Hire(FName Role);
private:
    UPROPERTY(Transient) TMap<FName, TObjectPtr<AFactoryWorker>> Workers;
    AFactoryWorkerSpawn* FindSpawn(FName Role) const;
};
