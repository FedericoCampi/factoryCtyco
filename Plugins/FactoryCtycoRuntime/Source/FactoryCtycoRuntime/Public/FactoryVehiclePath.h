#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryVehiclePath.generated.h"

class AFactoryTruckGate;
class AFactoryLoadingBelt;
class AFactoryTruckBay;
class UStaticMesh;
class USplineMeshComponent;
class UStaticMeshComponent;
class UInstancedStaticMeshComponent;
class UTextRenderComponent;
class UPoseableMeshComponent;
class USkeletalMesh;
class USplineComponent;
class USkeletalMeshComponent;
class UBoxComponent;
class UAnimationAsset;

/**
 * A vehicle (the user's truck) that drives along a spline drawn in the level. Move, add or delete
 * the points of Path in the viewport: the first point is where the vehicle starts (its rear axle),
 * and it drives until its rear axle passes the last point, then starts again (or goes round and
 * round when the spline is a closed loop). The height of each point is the ground it drives on.
 * Both axles stay on the line, so it turns like a vehicle; the wheels roll with the distance
 * travelled and the front ones steer into the curves. It brakes before a lowered AFactoryGateBarrier
 * whose arm crosses the line, waits until it is up and, once through, lets it come down.
 * At an AFactoryLoadingBelt whose far end is next to the line it stops with its cargo door there,
 * opens the door and takes the boxes the belt brings, stacking them inside ("n/10" over it). When
 * full it closes the door and drives on. Each trip starts empty.
 * Several vehicles can share a line (LeadPath: drive along another vehicle's line). They keep their
 * distance, never dock at the same belt, and each heads for the furthest free loading belt ahead:
 * when that one is taken it loads at an earlier free one, and moves on to the later one as soon as it
 * is free (unless it is full by then, when it drives straight on). At an AFactoryTruckBay whose maneuver joins the
 * line it stops with its rear axle at the join, backs into the bay along the maneuver and parks there (it heads for the
 * furthest free bay ahead, one per trip); a parked vehicle is off the line. Parked with the back of its cargo next
 * to the far end of a loading belt (BayLoadReach), it opens the door and loads from it; once full it drives out. The mesh's origin must be at the rear axle,
 * on the ground, facing +X (SK_Camion, from author_truck_loop.py).
 * A dump truck (bDumpTruck, SK_CamionVolcador from author_truck_dump.py) skips the loading belts and the plain bays: it
 * comes with a heap of LoadMesh pieces in its cargo, backs into a dump bay (AFactoryTruckBay::bDump), opens the rear
 * door and tips the cargo box (DumpBone, hinged at the back of its floor) up to DumpAngle; the pieces slide out and fall
 * (into the hopper behind it). Then the box comes down, the door shuts and it drives out; the next trip comes loaded again.
 * The rear door and the wraps ride on the box (CargoPivot follows DumpBone).
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryVehiclePath : public AActor
{
    GENERATED_BODY()
public:
    AFactoryVehiclePath();
    UPROPERTY(Category="Vehicle Path", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USplineComponent> Path;
    UPROPERTY(Category="Vehicle Path", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UPoseableMeshComponent> Vehicle;
    /** "n/10" over the cargo once the first box is in. */
    UPROPERTY(Category="Vehicle Path", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UTextRenderComponent> Counter;
    UPROPERTY(Category="Vehicle Path", EditAnywhere, BlueprintReadOnly) TObjectPtr<USkeletalMesh> VehicleMesh;
    /** cm per second. */
    UPROPERTY(Category="Vehicle Path", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float Speed = 300.0f;
    /** Road drawn along its own line (bent along it, so it follows the points when they move): a piece of
     *  road RoadPiece long along +X, repeated. A vehicle driving another one's line (LeadPath) draws none. */
    UPROPERTY(Category="Vehicle Path|Road", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> RoadMesh;
    UPROPERTY(Category="Vehicle Path|Road", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="20")) float RoadPiece = 200.0f;
    /** Height of the road over the line's points (cm): just over the ground so it does not flicker. */
    UPROPERTY(Category="Vehicle Path|Road", EditAnywhere, BlueprintReadOnly) float RoadLift = 0.5f;
    /** Drive along this other vehicle's line instead of this actor's own Path (for a second truck). */
    UPROPERTY(Category="Vehicle Path", EditInstanceOnly, BlueprintReadOnly) TObjectPtr<AFactoryVehiclePath> LeadPath;
    /** Seconds it waits at the first point when play starts (so a second truck comes behind). */
    UPROPERTY(Category="Vehicle Path", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float StartDelay = 0.0f;
    /** Room kept to the vehicle ahead on the same line (cm, bumper to back). Small, like a queue: the two
     *  loading belts are 5.7 m apart, so a truck at each leaves only ~45 cm between them. */
    UPROPERTY(Category="Vehicle Path", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float FollowGap = 30.0f;
    /** Seconds before it starts again from the first point (open line only). */
    UPROPERTY(Category="Vehicle Path", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float PauseBetweenTrips = 0.0f;
    /** Where along the line (cm from the first point) the vehicle stands in the editor, to check a spot. */
    UPROPERTY(Category="Vehicle Path", EditAnywhere, BlueprintReadOnly) float EditorPreviewDistance = 0.0f;
    /** The line it drives: LeadPath's, or its own Path. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path") USplineComponent* GetLine() const;
    /** Rear axle's distance along the line (cm). */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path") float GetDistanceAlong() const { return Distance; }
    /** Finds again the barriers and loading belts on its line (after an unlock). */
    void RefreshStops() { bGatesFound = false; }
    /** The barrier or door it is stopped at, waiting for it to open (for the events on the HUD). */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path") AFactoryTruckGate* GetWaitingGate() const { return WaitingGate.Get(); }
    /** The loading belt it is docked at or heading for, if any. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Cargo") AFactoryLoadingBelt* GetDockBelt() const;
    /** The bay it is heading for, backing into, parked at or leaving, if any. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Bays") AFactoryTruckBay* GetBay() const { return Bay.Get(); }
    /** Parked in a bay (off the line). */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Bays") bool IsParked() const { return BayState == EBayState::Parked; }
    /** Its bay's dock door should be up: it is heading for the bay and already through the last barrier before it (the
     *  entrance booth; with no barrier, as soon as it heads there), backing in or parked; not once it drives out. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Bays") bool WantsBayDoorOpen() const;
    /** Backing into a bay or driving out of it. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Bays") bool IsManeuvering() const { return BayState == EBayState::Reversing || BayState == EBayState::Leaving; }
    /** The driver in the cab (the character's mesh for now), seated: DriverAnim (A_TecJunior_Sit) loops on it. It
     *  stands at DriverTransform from the rear axle (the cab windows are open, author_truck_cab.py). No mesh: nobody. */
    UPROPERTY(Category="Vehicle Path|Driver", EditAnywhere, BlueprintReadOnly) TObjectPtr<USkeletalMesh> DriverMesh;
    UPROPERTY(Category="Vehicle Path|Driver", EditAnywhere, BlueprintReadOnly) TObjectPtr<UAnimationAsset> DriverAnim;
    /** Where the driver's feet origin goes (component space, cm): left seat, facing +X (the mesh faces +Y: yaw -90). */
    UPROPERTY(Category="Vehicle Path|Driver", EditAnywhere, BlueprintReadOnly) FTransform DriverTransform = FTransform(FRotator(0.0f, -90.0f, 0.0f), FVector(335.0f, -45.0f, 16.0f));
    UPROPERTY(Category="Vehicle Path|Driver", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USkeletalMeshComponent> Driver;
    /** Dump truck: unloads by tipping its cargo box at a dump bay (see the class comment). */
    UPROPERTY(Category="Vehicle Path|Dump", EditAnywhere, BlueprintReadOnly) bool bDumpTruck = false;
    /** The bone that tips the cargo box: it turns about its head, at the back of the cargo floor. */
    UPROPERTY(Category="Vehicle Path|Dump", EditAnywhere, BlueprintReadOnly) FName DumpBone = TEXT("Caja");
    /** How far the box tips (degrees). */
    UPROPERTY(Category="Vehicle Path|Dump", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0", ClampMax="70")) float DumpAngle = 50.0f;
    /** Seconds to tip it up, held up, and to bring it down. */
    UPROPERTY(Category="Vehicle Path|Dump", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.1")) float DumpRaiseSeconds = 4.0f;
    UPROPERTY(Category="Vehicle Path|Dump", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float DumpHoldSeconds = 2.5f;
    UPROPERTY(Category="Vehicle Path|Dump", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.1")) float DumpLowerSeconds = 3.0f;
    /** The load: pieces heaped on the cargo floor (SM_Cuarzo). */
    UPROPERTY(Category="Vehicle Path|Dump", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> LoadMesh;
    UPROPERTY(Category="Vehicle Path|Dump", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0", ClampMax="200")) int32 LoadPieces = 48;
    UPROPERTY(Category="Vehicle Path|Dump", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.05")) float LoadScale = 0.9f;
    /** A falling piece is gone this far under the lip it left (cm): inside the hopper. */
    UPROPERTY(Category="Vehicle Path|Dump", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="10")) float LoadFall = 180.0f;
    /** Rides on DumpBone: the rear door and the wraps hang from it (in the mesh's own space at rest). */
    UPROPERTY(Category="Vehicle Path|Dump", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneComponent> CargoPivot;
    /** The load's pieces, in world space. */
    UPROPERTY(Category="Vehicle Path|Dump", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Load;
    /** 0 down .. 1 tipped up to DumpAngle. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Dump") float GetDumpTilt() const { return DumpTilt; }
    /** Pieces still in the cargo, and the ones that went over the lip this trip. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Dump") int32 GetLoadInCargo() const;
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Dump") int32 GetLoadDumped() const;
    /** Where each piece that fell this trip was gone (LoadFall under the lip it left), in world space. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Dump") TArray<FVector> GetLoadLandings() const;
    /** Parked at a dump bay and tipping (or about to). */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Dump") bool IsDumping() const { return DumpPhase != EDumpPhase::None; }
    /** From the rear axle to the front bumper and to the back of the body (cm). The truck's box ends 1 m behind the rear
     *  axle: shorter, a barrier came down on its back (08/10). */
    UPROPERTY(Category="Vehicle Path|Barriers", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float FrontLength = 465.0f;
    UPROPERTY(Category="Vehicle Path|Barriers", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float RearLength = 105.0f;
    /** Traffic: trucks never drive into each other, on any line, backing into a bay or parked. Each one takes a rectangle
     *  (RearLength + FrontLength by twice HalfWidth) and does not move when the next step would bring it within TrafficGap
     *  of another truck in front of it (the way it moves). Stuck StuckSeconds, the truck behind on the line backs up
     *  BackOffDistance (or this one, when the other is stuck on it too). */
    UPROPERTY(Category="Vehicle Path|Traffic", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="10")) float HalfWidth = 105.0f;
    /** The truck's solid body for the character (the posed mesh itself does not collide): a box RearLength behind the
     *  rear axle to FrontLength ahead, twice HalfWidth wide and BodyHeight high. */
    UPROPERTY(Category="Vehicle Path|Traffic", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UBoxComponent> Body;
    UPROPERTY(Category="Vehicle Path|Traffic", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="10")) float BodyHeight = 235.0f;
    UPROPERTY(Category="Vehicle Path|Traffic", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float TrafficGap = 25.0f;
    UPROPERTY(Category="Vehicle Path|Traffic", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.5")) float StuckSeconds = 2.5f;
    UPROPERTY(Category="Vehicle Path|Traffic", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float BackOffDistance = 200.0f;
    /** The truck it is waiting for (stopped so as not to drive into it), if any. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Traffic") AFactoryVehiclePath* GetBlockedBy() const { return BlockedFor > 0.0f ? BlockedBy.Get() : nullptr; }
    /** Backing up to unblock (cm still to go). */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Traffic") float GetBackOff() const { return BackOff; }
    /** Wheels on the ground: each axle stands on whatever static floor is under it (a ramp, the yard) within GroundReach
     *  of the line, or on the road drawn along the line (RoadMesh) where that is higher (the driveway ramps at the yard
     *  gates are only road). So a line under the floor still drives on the floor. Off: on the line exactly. */
    UPROPERTY(Category="Vehicle Path|Ground", EditAnywhere, BlueprintReadOnly) bool bFollowGround = true;
    UPROPERTY(Category="Vehicle Path|Ground", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="10")) float GroundReach = 120.0f;
    /** Lifts its own line out of the floor: wherever the line runs under the floor it goes up to LineLift over it (points
     *  are added where the floor between two points rises above the line); where it is over the floor it stays (a road
     *  ramp). So the line shows in the viewport all along. */
    UFUNCTION(Category="Vehicle Path|Ground", BlueprintCallable, CallInEditor) void SnapLineToGround();
    /** Height of the line over the floor after SnapLineToGround (cm): above it, so it shows in the viewport. */
    UPROPERTY(Category="Vehicle Path|Ground", EditAnywhere, BlueprintReadOnly) float LineLift = 5.0f;
    /** How far before a lowered barrier the bumper stops (cm). */
    UPROPERTY(Category="Vehicle Path|Barriers", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float StopGap = 70.0f;
    /** cm/s² when braking for a barrier and when setting off again. */
    UPROPERTY(Category="Vehicle Path|Barriers", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float Braking = 220.0f;
    UPROPERTY(Category="Vehicle Path|Barriers", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float Acceleration = 120.0f;
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) int32 CargoCapacity = 10;
    /** From the rear axle to the middle of the cargo door, forward (cm): lined up with the belt when docked. */
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly) float CargoDoorOffset = 107.0f;
    /** How close a loading belt's far end must be to the line to dock there (cm). */
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="10")) float DockReach = 250.0f;
    /** Parked in a bay: how close a loading belt's far end must be to the rear axle to load from it (cm). */
    UPROPERTY(Category="Vehicle Path|Bays", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="10")) float BayLoadReach = 250.0f;
    /** Seconds the rear door takes to go up or down. */
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.1")) float DoorSeconds = 1.3f;
    /** Rear roll-up door (author_truck_shutter.py), at the back of the cargo box: slats (RearSlatMesh) stacked on a
     *  bottom bar (RearBottomMesh) between two guides under a header (RearDoorMesh). Opening, they slide up and each
     *  slat that is wholly behind the header goes. The cargo box's roof and side stay shut. */
    UPROPERTY(Category="Vehicle Path|Rear Door", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> RearDoorMesh;
    UPROPERTY(Category="Vehicle Path|Rear Door", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> RearSlatMesh;
    UPROPERTY(Category="Vehicle Path|Rear Door", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> RearBottomMesh;
    /** Middle of the door opening's top edge, in the door's plane (component space, cm: from the rear axle, on the
     *  floor): the guides and header hang from here, and the slats close the opening below it. */
    UPROPERTY(Category="Vehicle Path|Rear Door", EditAnywhere, BlueprintReadOnly) FVector RearDoorTop = FVector(-95.0f, 0.0f, 230.0f);
    /** Height of the opening (cm). */
    UPROPERTY(Category="Vehicle Path|Rear Door", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float RearDoorHeight = 138.9f;
    /** Height of the header over the opening (cm): the slats go up behind it. */
    UPROPERTY(Category="Vehicle Path|Rear Door", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float RearHeader = 10.0f;
    UPROPERTY(Category="Vehicle Path|Rear Door", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> RearDoor;
    UPROPERTY(Category="Vehicle Path|Rear Door", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> RearSlats;
    UPROPERTY(Category="Vehicle Path|Rear Door", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> RearBottom;
    /** How far the rear door's bottom bar is up from shut (cm). */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Rear Door") float GetRearDoorRise() const { return RearRise; }
    /** Inside of the cargo box, from the rear axle (cm): floor height and the span boxes are laid over. */
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly) float CargoFloor = 99.0f;
    /** Wrap on both sides of the cargo box: a one-sided panel facing -Y (SM_PloteoLado) with its material. The
     *  one on the door side (-Y) moves with the door bone; the other is turned to face +Y. Empty mesh: no wrap. */
    UPROPERTY(Category="Vehicle Path|Wrap", EditAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMesh> WrapMesh;
    /** Middle of the panel on the right side (component space, cm); the door side is its mirror in Y. The
     *  side skin is ~80-85 cm out (ribs included): nearer, the panel hides inside the body. */
    UPROPERTY(Category="Vehicle Path|Wrap", EditAnywhere, BlueprintReadOnly) FVector WrapCenter = FVector(107.0f, 86.0f, 158.0f);
    UPROPERTY(Category="Vehicle Path|Wrap", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> WrapDoor;
    UPROPERTY(Category="Vehicle Path|Wrap", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> WrapSide;
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly) float CargoFrontX = 258.0f;
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly) float CargoBackX = -80.0f;
    /** Rows across the cargo (y, cm): the far one fills first, then the one by the door. */
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly) TArray<float> CargoRows = {46.0f, -14.0f};
    /** Seconds a box takes to hop from the belt to its place. */
    UPROPERTY(Category="Vehicle Path|Cargo", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.05")) float HopSeconds = 0.6f;
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Cargo") int32 GetCargoCount() const { return Loaded; }
    /** Docked with the door fully open and not full. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Cargo") bool IsReadyToLoad() const;
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Cargo") bool IsDocked() const { return bDocked; }
    /** Loads by the rear door (parked in a bay) instead of the side one. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Cargo") bool UsesRearDoor() const { return bBayLoading; }
    /** 0 closed .. 1 open. */
    UFUNCTION(BlueprintCallable, Category="Vehicle Path|Cargo") float GetDoorOpenness() const { return DoorOpen; }
    /** Boxes that still fit, not counting the ones on their way in. */
    int32 FreeCargoSlots() const { return CargoCapacity - Loaded - Flights.Num(); }
    /** A belt hands a box over (from where it is); false if it cannot take it now. */
    bool ReceiveBox(UStaticMesh* Mesh, const FTransform& FromWorld);
    /** Distance between the axles (cm). */
    UPROPERTY(Category="Vehicle Path|Wheels", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float Wheelbase = 333.9f;
    UPROPERTY(Category="Vehicle Path|Wheels", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float FrontWheelRadius = 37.4f;
    UPROPERTY(Category="Vehicle Path|Wheels", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float RearWheelRadius = 35.9f;
    /** Largest steering angle of the front wheels (degrees). */
    UPROPERTY(Category="Vehicle Path|Wheels", EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0", ClampMax="80")) float MaxSteer = 38.0f;
    UPROPERTY(Category="Vehicle Path|Wheels", EditAnywhere, BlueprintReadOnly) TArray<FName> FrontWheels = {TEXT("Rueda_DI"), TEXT("Rueda_DD")};
    UPROPERTY(Category="Vehicle Path|Wheels", EditAnywhere, BlueprintReadOnly) TArray<FName> RearWheels = {TEXT("Rueda_TI"), TEXT("Rueda_TD")};
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
private:
    /** Rear axle's distance along the line. */
    float Distance = 0.0f;
    float CurrentSpeed = 0.0f;
    /** How far the rear axle may still go this tick without passing a stop (loading belt, barrier, vehicle ahead).
     *  A long frame must not carry it past a stop: braking alone relied on small steps. */
    float MaxAdvance = TNumericLimits<float>::Max();
    struct FGateStop
    {
        TWeakObjectPtr<AFactoryTruckGate> Gate;
        float At = 0.0f;         // where the arm crosses the line
        bool bWasUnder = false;
    };
    TArray<FGateStop> Gates;
    TWeakObjectPtr<AFactoryTruckGate> WaitingGate;
    bool bGatesFound = false;
    struct FDock
    {
        TWeakObjectPtr<AFactoryLoadingBelt> Belt;
        float At = 0.0f;         // where the belt's far end meets the line
    };
    TArray<FDock> Docks;
    struct FBayStop
    {
        TWeakObjectPtr<AFactoryTruckBay> Bay;
        float At = 0.0f;         // where its maneuver joins the line
    };
    TArray<FBayStop> Bays;
    enum class EBayState : uint8 { None, Reversing, Parked, Leaving };
    EBayState BayState = EBayState::None;
    /** The bay reserved, being backed into, parked at or left. */
    TWeakObjectPtr<AFactoryTruckBay> Bay;
    float BayAt = 0.0f;      // rear axle's distance along the line where the maneuver joins it
    float BayS = 0.0f;       // rear axle's distance along the maneuver (0: parked)
    float ParkedFor = 0.0f;
    bool bBayDone = false;   // parked once this trip
    /** Parked and loading from this belt (docked to it outside Docks). */
    TWeakObjectPtr<AFactoryLoadingBelt> BayBelt;
    bool bBayLoading = false;
    /** Parked: docks at the last loading belt ending behind it, if any is free. */
    void DockAtBayBelt();
    void UndockBayBelt();
    void FindBays();
    /** Top speed allowed by the bay ahead; starts backing in when it gets there. */
    float BaySpeedLimit();
    /** Backing in, parked or driving out: moves along the maneuver instead of the line. */
    void TickBay(float DeltaSeconds);
    void ReleaseBay();
    /** Off the line (parked in a bay): it does not hold up the vehicles on the line. */
    bool IsOffLine() const { return BayState == EBayState::Parked; }
    /** Whether no vehicle on the line is around At (to drive out of a bay there). */
    bool LineClearAt(float At) const;
    /** Rear and front axle positions with the rear axle at Along on the line (or on the bay's maneuver). */
    void AxlePoints(float Along, FVector& Rear, FVector& Front) const;
    int32 DockIndex = INDEX_NONE;   // docked at Docks[DockIndex]
    int32 ReservedIndex = INDEX_NONE;   // heading for Docks[ReservedIndex]
    bool bDocked = false, bServed = false, bDoorWantOpen = false;
    /** This trip's load already counted as delivered (the mission). */
    bool bDelivered = false;
    void Deliver();
    float DoorOpen = 0.0f;
    int32 Loaded = 0;
    struct FFlight
    {
        TObjectPtr<UStaticMeshComponent> Box;
        FTransform From;         // relative to Vehicle
        int32 Slot = 0;
        float T = 0.0f;
    };
    TArray<FFlight> Flights;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Cargo;
    void FindDocks();
    /** Whether Docks[Index] is ahead, not taken by another vehicle and its stop is clear of them. */
    bool DockFreeFor(int32 Index) const;
    void Reserve(int32 Index);
    /** Top speed that keeps FollowGap to the vehicle ahead on the same line. */
    float FollowSpeedLimit();
    /** Whether the first stretch of the line is clear to start a trip there. */
    bool StartIsClear() const;
    /** Top speed allowed by the loading stop ahead; docks there when it arrives. */
    float DockSpeedLimit();
    void UpdateCargo(float DeltaSeconds);
    FTransform SlotTransform(int32 Slot) const;
    /** Empties the cargo for a new trip. */
    void ResetCargo();
    /** Barriers whose arm (down) crosses the line; done on the first tick, once they have begun play. */
    void FindGates();
    /** Top speed allowed by the barriers ahead; tells them when the vehicle is under or through. */
    float GateSpeedLimit();
    float RearSpin = 0.0f, FrontSpin = 0.0f;   // degrees
    float Paused = 0.0f;
    /** Component-space rotation of each wheel bone in the reference pose. */
    TMap<FName, FQuat> RestRotation;
    /** The rear door's rise last placed (cm; -1: not placed yet). */
    float RearRise = -1.0f;
    /** Places the rear door's slats and bottom bar for Open (0 shut .. 1 up). */
    void PlaceRearDoor(float Open);
    /** World position on the line at Along, continuing straight past its ends. */
    FVector PointAt(float Along) const;
    FVector DirectionAt(float Along) const;
    enum class EDumpPhase : uint8 { None, Opening, Raising, Holding, Lowering, Closing };
    EDumpPhase DumpPhase = EDumpPhase::None;
    float DumpTilt = 0.0f, DumpTimer = 0.0f;
    /** DumpBone's rest rotation (component space); no bone: no tipping. */
    FQuat DumpRest = FQuat::Identity;
    bool bHasDumpBone = false;
    struct FPiece
    {
        FTransform Home;          // in the cargo (CargoPivot space)
        uint8 State = 0;          // 0 in the cargo, 1 sliding to the lip, 2 falling, 3 gone
        float Slide = 0.0f;       // how far it slid back (cm) and how fast
        float SlideSpeed = 0.0f;
        float Release = 0.0f;     // tilt (0..1) at which it starts to slide
        FVector Position = FVector::ZeroVector, Velocity = FVector::ZeroVector;   // falling (world)
        FQuat Rotation = FQuat::Identity;
        float LipZ = 0.0f;
        FVector Landed = FVector::ZeroVector;   // where it was gone
    };
    TArray<FPiece> LoadState;
    /** Seats the driver (DriverMesh playing DriverAnim at DriverTransform). */
    void PlaceDriver();
    /** Puts the rear door and wraps on CargoPivot, and CargoPivot on DumpBone (if the mesh has it). */
    void RigCargo();
    /** Heaps the load in the cargo (a new trip). */
    void FillLoad();
    /** Parked at a dump bay: opens, tips, holds, lowers, shuts; true once done. */
    bool TickDump(float DeltaSeconds);
    /** Moves the load's pieces (and tips the box to DumpTilt). */
    void UpdateLoad(float DeltaSeconds);
    void PoseDump();
    /** Traffic (see HalfWidth). */
    float BlockedFor = 0.0f, BackOff = 0.0f;
    TWeakObjectPtr<AFactoryVehiclePath> BlockedBy;
    /** Where its axles were last placed (world), for the other trucks. */
    FVector LastRear = FVector::ZeroVector, LastFront = FVector::ZeroVector;
    bool bPlaced = false;
    /** Whether axles at Rear/Front, moving along Motion, would come within TrafficGap of another truck ahead of it. */
    bool WouldHit(const FVector& Rear, const FVector& Front, const FVector& Motion, AFactoryVehiclePath*& Other) const;
    /** Whether a Step along the bay's maneuver would drive into another truck (then it waits). */
    bool ManeuverBlocked(float Step, float DeltaSeconds);
    /** Stopped by Other this tick: after StuckSeconds the one behind backs up. */
    void NoteBlocked(AFactoryVehiclePath* Other, float DeltaSeconds);
    /** What the wheel at Point stands on: the floor under it (within GroundReach) or, bOnRoad, the road drawn along the
     *  line there if higher; Point's own height when there is nothing. */
    float GroundZ(const FVector& Point, bool bOnRoad) const;
    /** The first fixed floor (a static component: not a barrier arm, a door or a truck) between From and To. */
    bool TraceFloor(const FVector& From, const FVector& To, float& Z) const;
    /** Places the vehicle with its rear axle at Along and turns the wheels. */
    void Place(float Along, float Steer);
    void CacheRestPose();
    /** The vehicle's bones can be read and posed (its mesh is set and its pose is allocated: right after a reimport
     *  or before the component registers it is not, and posing it then asserts). */
    bool PoseReady() const;
    /** Lays the road pieces along the line (construction script components, rebuilt on every change). */
    void BuildRoad();
};
