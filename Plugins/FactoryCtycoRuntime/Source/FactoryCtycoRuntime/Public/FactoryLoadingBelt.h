#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryLoadingBelt.generated.h"

class AFactoryVehiclePath;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UStaticMesh;
class UStaticMeshComponent;
class UTextRenderComponent;

/**
 * Loading belt for the trucks. With a box in hand, E next to any part of it sets the box there (there
 * or not a truck: boxes wait at the end for the next one); the belt carries it to its far end
 * (x Length) and passes it on: to a belt whose load end is right there (belts link on their own, or
 * through NextBelt), or, at a last belt, to the vehicle docked there, which stows it in its cargo.
 * Where several belts start at its end, the branches are tried in order, the one leading to the stop
 * furthest along the trucks' line (nearest the barrier) first: a box goes to the first branch with a
 * truck waiting and room for it (counting the boxes already on the way); with none, it queues on the
 * first branch, to wait for the next truck. When the chosen branch's row is full the box waits where it is
 * (it never jumps over a full belt). A vehicle docks at a last belt whose far end is next to
 * its line (AFactoryVehiclePath finds it).
 * Move, turn and stretch the actor (scale X) freely: boxes keep their size and spacing. It can be tilted
 * (pitch: the boxes ride up or down the slope) and raised: under a raised belt, posts (Supports) reach down
 * to the floor, so there is room to walk beneath it. A corner belt (TurnDegrees) follows a quarter circle;
 * scale it evenly to make it bigger, and set scale Y to -1 to make it turn the other way.
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryLoadingBelt : public AActor
{
    GENERATED_BODY()
public:
    AFactoryLoadingBelt();
    UPROPERTY(Category="Loading Belt", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Belt;
    UPROPERTY(Category="Loading Belt", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> Prompt;
    /** Posts from a raised belt down to the floor (rebuilt when the belt moves). */
    UPROPERTY(Category="Loading Belt|Supports", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Supports;
    /** From the load end to the far end, along +X, before scaling (cm). On a corner: along its centre line. */
    UPROPERTY(Category="Loading Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="50")) float Length = 300.0f;
    /** 0: straight. Otherwise the belt is an arc that turns this much (degrees; negative: towards local -Y). */
    UPROPERTY(Category="Loading Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="-180", ClampMax="180")) float TurnDegrees = 0.0f;
    /** Post under a raised belt: its bounds are stretched from the floor to the belt's underside (local Z 0). */
    UPROPERTY(Category="Loading Belt|Supports", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> SupportMesh;
    /** Empty: the belt's own steel (slot M_CintaAcero) when it has one. */
    UPROPERTY(Category="Loading Belt|Supports", EditAnywhere, BlueprintReadOnly) TObjectPtr<UMaterialInterface> SupportMaterial;
    /** One post near each end and one every this many cm between them (world cm). */
    UPROPERTY(Category="Loading Belt|Supports", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="50")) float SupportSpacing = 250.0f;
    /** Post width (cm); 0 keeps SupportMesh's own width. */
    UPROPERTY(Category="Loading Belt|Supports", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float SupportWidth = 12.0f;
    /** Posts are only placed where the belt is at least this high over the floor (cm). */
    UPROPERTY(Category="Loading Belt|Supports", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float SupportMinGap = 10.0f;
    /** Point of the centre line (local, unscaled) at LocalAlong cm from the load end, at deck height; OutYaw: its heading. */
    FVector LocalAt(float LocalAlong, float* OutYaw = nullptr) const;
    /** World point of the deck at Along world cm from the load end. */
    UFUNCTION(BlueprintCallable, Category="Loading Belt") FVector WorldAt(float Along) const;
    /** Places the posts again (under a raised belt). */
    UFUNCTION(BlueprintCallable, Category="Loading Belt") void BuildSupports();
    virtual void OnConstruction(const FTransform& Transform) override;
    /** Height of the rollers' top (cm): where boxes ride. */
    UPROPERTY(Category="Loading Belt", EditAnywhere, BlueprintReadOnly) float DeckHeight = 88.0f;
    /** cm per second, in the world. */
    UPROPERTY(Category="Loading Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float Speed = 80.0f;
    /** Room one box takes on the belt, box plus gap (cm, in the world): a ~40 cm box and a small gap. */
    UPROPERTY(Category="Loading Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="10")) float BoxSpacing = 58.0f;
    /** How close to the belt the character must be (cm). */
    UPROPERTY(Category="Loading Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="50")) float InteractionRadius = 130.0f;
    /** Apparent roller turns per second while it runs ("Velocidad" of the roller material). */
    UPROPERTY(Category="Loading Belt", EditAnywhere, BlueprintReadOnly) float RollerSpeed = 1.5f;
    /** Belt this one feeds. Empty: every belt whose load end is within LinkReach of this one's far end. */
    UPROPERTY(Category="Loading Belt", EditInstanceOnly, BlueprintReadOnly) TObjectPtr<AFactoryLoadingBelt> NextBelt;
    UPROPERTY(Category="Loading Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="10")) float LinkReach = 120.0f;
    /** The vehicle docked at the far end right now (set by the vehicle). */
    UPROPERTY(Category="Loading Belt", VisibleInstanceOnly, Transient, BlueprintReadOnly) TObjectPtr<AFactoryVehiclePath> Docked;
    /** The vehicle on its way to dock here (set by the vehicle). */
    UPROPERTY(Category="Loading Belt", VisibleInstanceOnly, Transient, BlueprintReadOnly) TObjectPtr<AFactoryVehiclePath> Reserved;
    UFUNCTION(BlueprintCallable, Category="Loading Belt") int32 GetBoxCount() const { return Boxes.Num(); }
    /** The first belt this one hands its boxes to, if any (see GetOutputs). */
    UFUNCTION(BlueprintCallable, Category="Loading Belt") AFactoryLoadingBelt* GetNext() const { return Outputs.IsEmpty() ? nullptr : Outputs[0].Get(); }
    /** Every belt this one hands boxes to (NextBelt, or those starting at its far end). */
    UFUNCTION(BlueprintCallable, Category="Loading Belt") TArray<AFactoryLoadingBelt*> GetOutputs() const;
    /** Whether a truck is docked at a last belt this one leads to with room for the boxes already on the way. */
    UFUNCTION(BlueprintCallable, Category="Loading Belt") bool HasWaitingTruck() const;
    /** Boxes on this belt and on every belt after it. */
    UFUNCTION(BlueprintCallable, Category="Loading Belt") int32 BoxesAhead() const;
    /** World position where boxes leave the belt, at the far end. */
    UFUNCTION(BlueprintCallable, Category="Loading Belt") FVector GetDeliveryPoint() const;
    /** Finds again the belts it feeds (after an unlock). */
    void RefreshLinks();
    /** World position of the load end. */
    FVector GetLoadPoint() const;
    /** Distance (2D, cm) from User to the belt, and how far along it (world cm from the load end) that is. */
    float DistanceTo(const AActor* User, float& OutAlong) const;
    bool InReach(const AActor* User) const;
    /** E with a box in hand next to the belt: puts it where the character is. Returns whether it did anything. */
    UFUNCTION(BlueprintCallable, Category="Loading Belt") bool TryLoad(AActor* User);
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Boxes;
    /** World cm from the load end, furthest first. */
    TArray<float> Travelled;
    /** Each box's own small turn on the belt (degrees), on top of the belt's heading where it is. */
    TArray<float> Jitter;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> RollerMaterial;
    UPROPERTY(Transient) TArray<TObjectPtr<AFactoryLoadingBelt>> Outputs;
    bool bRunning = false;
    float Stretch() const;
    float WorldLength() const { return Length * Stretch(); }
public:
    /** Whether a box fits at Along (no box within BoxSpacing). */
    UFUNCTION(BlueprintCallable, Category="Loading Belt") bool RoomAt(float Along) const;
private:
public:
    /** The output for the box at the far end (see the class comment), or null to wait. */
    AFactoryLoadingBelt* ChooseOutput() const;
    /** A box set this close to the load end of a branch (cm) goes where its crossing would send it. */
    UPROPERTY(Category="Loading Belt", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float CrossingZone = 70.0f;
private:
    int32 BoxesAhead(TSet<const AFactoryLoadingBelt*>& Seen) const;
    /** How far along a truck line the stop this belt leads to is (the furthest, for a branch); -1 without one. */
    float StopOrder(TSet<const AFactoryLoadingBelt*>& Seen) const;
    bool HasWaitingTruck(int32 OnTheWay, TSet<const AFactoryLoadingBelt*>& Seen) const;
    void AddBox(UStaticMesh* Mesh, float Along, float Yaw);
};
