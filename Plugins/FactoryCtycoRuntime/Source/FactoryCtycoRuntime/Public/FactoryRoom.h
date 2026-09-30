#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryRoom.generated.h"

class UBoxComponent;
class UStaticMeshComponent;

/**
 * An indoor room seen from the isometric camera: while the player (or whoever the camera follows) is inside
 * Area, the actors in HideWhenInside (its roof) are hidden, so the room can be seen from above.
 */
UCLASS()
class FACTORYCTYCORUNTIME_API AFactoryRoom : public AActor
{
    GENERATED_BODY()
public:
    AFactoryRoom();
    UPROPERTY(Category="Room", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UBoxComponent> Area;
    UPROPERTY(Category="Room", EditAnywhere, BlueprintReadWrite) TArray<TObjectPtr<AActor>> HideWhenInside;
    /** Whether the roof is hidden now. */
    UFUNCTION(BlueprintCallable, Category="Room") bool IsOpen() const { return bOpen; }
    virtual void Tick(float DeltaSeconds) override;
private:
    bool bOpen = false;
    bool Contains(const AActor* Actor) const;
};

/**
 * A hinged door that opens by itself when a pawn (the player or a worker) comes close and closes behind.
 * The leaf's origin is the hinge; it swings OpenYaw degrees. It has no collision (the doorway stays walkable).
 */
UCLASS()
class FACTORYCTYCORUNTIME_API AFactoryAutoDoor : public AActor
{
    GENERATED_BODY()
public:
    AFactoryAutoDoor();
    UPROPERTY(Category="Door", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Leaf;
    UPROPERTY(Category="Door", EditAnywhere, BlueprintReadWrite) float OpenYaw = 95.0f;
    /** How close a pawn must be (cm, from the middle of the doorway) for the door to open. */
    UPROPERTY(Category="Door", EditAnywhere, BlueprintReadWrite, meta=(ClampMin="50")) float OpenRadius = 230.0f;
    UPROPERTY(Category="Door", EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0.1")) float OpenSeconds = 0.6f;
    /** Door width (cm): the middle of the doorway is this far from the hinge along the closed leaf. */
    UPROPERTY(Category="Door", EditAnywhere, BlueprintReadWrite) float Width = 110.0f;
    /** 0 shut .. 1 open. */
    UFUNCTION(BlueprintCallable, Category="Door") float GetOpenness() const { return Openness; }
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
private:
    float Openness = 0.0f;
    float ClosedYaw = 0.0f;
};
