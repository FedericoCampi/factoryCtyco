#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FactoryWalkway.generated.h"

class UInstancedStaticMeshComponent;
class UStaticMesh;

/**
 * A walkway built from pieces (deck, rail span, post) that follows its rails: each rail is a line in actor space (cm)
 * and the deck fills between them. In the viewport the rails and the ends have diamond handles: drag one and the rail
 * or end moves there (the deck widens, narrows, gets longer or shorter); then the handle goes back to its place.
 * Posts go at both ends of each rail and evenly between, about PostSpacing apart. The pieces collide with simple
 * boxes, so the deck can be walked on. Pieces: Scripts/author_pasarela_modular.py.
 * With a legs piece (LegMesh) the deck can go up or down (DeckHeight, or the height handle): the legs stretch from the
 * ground to the deck and the rails go with it, so there is room to walk underneath.
 */
UCLASS(Abstract)
class FACTORYCTYCORUNTIME_API AFactoryWalkway : public AActor
{
    GENERATED_BODY()
public:
    AFactoryWalkway();

    /** Pieces, each running along +X and centred on X and Y; a rail's outside is -Y. Empty: the project's own. */
    UPROPERTY(Category="Walkway|Pieces", EditAnywhere, BlueprintReadWrite) TObjectPtr<UStaticMesh> DeckMesh;
    UPROPERTY(Category="Walkway|Pieces", EditAnywhere, BlueprintReadWrite) TObjectPtr<UStaticMesh> RailMesh;
    UPROPERTY(Category="Walkway|Pieces", EditAnywhere, BlueprintReadWrite) TObjectPtr<UStaticMesh> PostMesh;
    /** Legs under one deck piece, from the ground up to PieceLegTop (the deck piece starts there). Empty: the deck
     *  piece reaches the ground and the height is the pieces' own. */
    UPROPERTY(Category="Walkway|Pieces", EditAnywhere, BlueprintReadWrite) TObjectPtr<UStaticMesh> LegMesh;
    /** In the pieces (cm): the top of the deck and where the legs end. */
    UPROPERTY(Category="Walkway|Pieces", EditAnywhere, BlueprintReadWrite) float PieceDeckTop = 0.0f;
    UPROPERTY(Category="Walkway|Pieces", EditAnywhere, BlueprintReadWrite) float PieceLegTop = 0.0f;
    /** Height of the deck's top over the actor (cm), with a legs piece: the legs stretch, the deck and the rails go
     *  up or down with it. 0: the pieces' own (PieceDeckTop). */
    UPROPERTY(Category="Walkway", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float DeckHeight = 0.0f;
    /** Viewport handle over the walkway: drag it up or down for the deck's height. */
    UPROPERTY(Category="Walkway|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector HeightHandle = FVector::ZeroVector;
    /** Size of one deck piece (cm): length along X and width across. */
    UPROPERTY(Category="Walkway|Pieces", EditAnywhere, BlueprintReadWrite) FVector2D DeckPieceSize = FVector2D(127.0f, 138.3f);
    /** How far the deck reaches past each rail's centre line (cm). */
    UPROPERTY(Category="Walkway|Pieces", EditAnywhere, BlueprintReadWrite) float DeckPastRail = 15.0f;
    /** Length of one rail span piece and width of a post (cm). */
    UPROPERTY(Category="Walkway|Pieces", EditAnywhere, BlueprintReadWrite) float RailPieceLength = 127.0f;
    UPROPERTY(Category="Walkway|Pieces", EditAnywhere, BlueprintReadWrite) float PostWidth = 23.0f;
    UPROPERTY(Category="Walkway|Pieces", EditAnywhere, BlueprintReadWrite, meta=(ClampMin="50")) float PostSpacing = 148.0f;

    UPROPERTY(Category="Walkway", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Deck;
    UPROPERTY(Category="Walkway", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Rails;
    UPROPERTY(Category="Walkway", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Posts;
    UPROPERTY(Category="Walkway", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Legs;

    /** Places every piece again from the rails. */
    UFUNCTION(Category="Walkway", BlueprintCallable) void Rebuild();
    virtual void OnConstruction(const FTransform& Transform) override;
protected:
    /** A dragged handle becomes its rail or end; then the rails are kept apart and the handles go back in place. */
    virtual void ApplyHandles() {}
    /** Adds the deck and rail pieces (the instances were just cleared). */
    virtual void BuildPieces() {}
    /** Folder of the project's pieces and their names (DeckMesh etc. empty). */
    virtual FString PieceFolder() const { return TEXT("/Game/FactoryCtyco/Environments/Pasarelas/Modular"); }
    virtual FString PiecePrefix() const { return TEXT("SM_Pasarela"); }
    /** Where the height handle goes (actor space, across): over the middle of the walkway. */
    virtual FVector2D HeightHandleAt() const { return FVector2D::ZeroVector; }
    /** How far the deck and the rails are raised over the pieces' own height (cm; 0 without legs). */
    float Lift() const;
    /** Deck from From to To (its middle line), Width across. */
    void AddDeck(FVector2D From, FVector2D To, float Width);
    /** Rail from From to To with its outside towards Outside; bFirstPost: a post at From too. */
    void AddRail(FVector2D From, FVector2D To, FVector2D Outside, bool bFirstPost);
    /** Whether Handle was dragged since it was last put at Placed (zero: not yet placed, so not dragged). */
    static bool Dragged(const FVector& Handle, const FVector& Placed) { return !Placed.IsZero() && !Handle.Equals(Placed, 0.5f); }
    static constexpr float MinWidth = 60.0f;   // between the two rails of an arm
private:
    /** The height handle becomes DeckHeight, kept between the lowest the legs allow and MaxDeckHeight. */
    void ApplyHeight();
    FVector PlacedHeight = FVector::ZeroVector;
    static constexpr float MaxDeckHeight = 2000.0f;
};

/**
 * An L-shaped walkway. Arm A runs along +X and arm B along +Y from the outer corner:
 * - OuterA / InnerA: Y of arm A's outer and inner rails; OuterB / InnerB: X of arm B's outer and inner rails;
 * - EndA: X where arm A ends; EndB: Y where arm B ends (the ends stay open).
 * Handles: one in the middle of each rail (drag it across) and one at each end. Rails can be turned off one by one
 * (to join the walkway to a platform).
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryWalkwayL : public AFactoryWalkway
{
    GENERATED_BODY()
public:
    UPROPERTY(Category="Walkway", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float OuterA = -255.0f;
    UPROPERTY(Category="Walkway", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float InnerA = -120.0f;
    UPROPERTY(Category="Walkway", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float OuterB = -249.0f;
    UPROPERTY(Category="Walkway", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float InnerB = -136.0f;
    UPROPERTY(Category="Walkway", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float EndA = 263.0f;
    UPROPERTY(Category="Walkway", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float EndB = 269.0f;
    UPROPERTY(Category="Walkway|Rails", EditAnywhere, BlueprintReadWrite) bool bOuterRailA = true;
    UPROPERTY(Category="Walkway|Rails", EditAnywhere, BlueprintReadWrite) bool bInnerRailA = true;
    UPROPERTY(Category="Walkway|Rails", EditAnywhere, BlueprintReadWrite) bool bOuterRailB = true;
    UPROPERTY(Category="Walkway|Rails", EditAnywhere, BlueprintReadWrite) bool bInnerRailB = true;

    /** Viewport handles (actor space): drag them; they go back to the middle of their rail or end. */
    UPROPERTY(Category="Walkway|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector OuterRailAHandle = FVector::ZeroVector;
    UPROPERTY(Category="Walkway|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector InnerRailAHandle = FVector::ZeroVector;
    UPROPERTY(Category="Walkway|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector OuterRailBHandle = FVector::ZeroVector;
    UPROPERTY(Category="Walkway|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector InnerRailBHandle = FVector::ZeroVector;
    UPROPERTY(Category="Walkway|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector EndAHandle = FVector::ZeroVector;
    UPROPERTY(Category="Walkway|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector EndBHandle = FVector::ZeroVector;
protected:
    virtual void ApplyHandles() override;
    virtual void BuildPieces() override;
    virtual FVector2D HeightHandleAt() const override { return FVector2D((OuterB + InnerB) / 2, (OuterA + InnerA) / 2); }
private:
    FVector Placed[6];
};

/**
 * A straight walkway along X: the deck between its two rails, from StartX to EndX (both ends open).
 * - LeftRailY / RightRailY: Y of the rails (left is the smaller Y);
 * - StartX / EndX: where it begins and ends.
 * Handles: one in the middle of each rail (drag it across) and one at each end (drag it along).
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryWalkwayStraight : public AFactoryWalkway
{
    GENERATED_BODY()
public:
    AFactoryWalkwayStraight();
    UPROPERTY(Category="Walkway", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float LeftRailY = -110.0f;
    UPROPERTY(Category="Walkway", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float RightRailY = 110.0f;
    UPROPERTY(Category="Walkway", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float StartX = -495.0f;
    UPROPERTY(Category="Walkway", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float EndX = 495.0f;
    UPROPERTY(Category="Walkway|Rails", EditAnywhere, BlueprintReadWrite) bool bLeftRail = true;
    UPROPERTY(Category="Walkway|Rails", EditAnywhere, BlueprintReadWrite) bool bRightRail = true;

    UPROPERTY(Category="Walkway|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector LeftRailHandle = FVector::ZeroVector;
    UPROPERTY(Category="Walkway|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector RightRailHandle = FVector::ZeroVector;
    UPROPERTY(Category="Walkway|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector StartHandle = FVector::ZeroVector;
    UPROPERTY(Category="Walkway|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector EndHandle = FVector::ZeroVector;
protected:
    virtual void ApplyHandles() override;
    virtual void BuildPieces() override;
    virtual FString PiecePrefix() const override { return TEXT("Recta/SM_PasarelaRecta"); }
    virtual FVector2D HeightHandleAt() const override { return FVector2D((StartX + EndX) / 2, (LeftRailY + RightRailY) / 2); }
private:
    FVector Placed[4];
};
