#pragma once

#include "CoreMinimal.h"
#include "FactoryWalkway.h"
#include "FactoryPlatform.generated.h"

class UInstancedStaticMeshComponent;
class USplineComponent;
class UStaticMesh;

/** Which rail pieces a platform or a railing uses. */
UENUM(BlueprintType)
enum class EFactoryRailStyle : uint8
{
    Escalera UMETA(DisplayName="Escalera (paneles)"),
    Verde UMETA(DisplayName="Pasarela verde"),
    LElevada UMETA(DisplayName="Pasarela L elevada"),
    Propia UMETA(DisplayName="Propia (piezas a mano)")
};

/** Rail pieces (a span between two posts and a post, each running along +X, outside towards -Y) and their sizes. */
USTRUCT(BlueprintType)
struct FACTORYCTYCORUNTIME_API FFactoryRailPieces
{
    GENERATED_BODY()
    UPROPERTY(Category="Rail", EditAnywhere, BlueprintReadWrite) TObjectPtr<UStaticMesh> RailMesh;
    UPROPERTY(Category="Rail", EditAnywhere, BlueprintReadWrite) TObjectPtr<UStaticMesh> PostMesh;
    UPROPERTY(Category="Rail", EditAnywhere, BlueprintReadWrite) float RailPieceLength = 90.0f;
    UPROPERTY(Category="Rail", EditAnywhere, BlueprintReadWrite) float PostWidth = 23.0f;
    UPROPERTY(Category="Rail", EditAnywhere, BlueprintReadWrite, meta=(ClampMin="30")) float PostSpacing = 114.0f;
    /** Height of the floor the rail stands on, in the pieces (cm): the pieces go down by this much. */
    UPROPERTY(Category="Rail", EditAnywhere, BlueprintReadWrite) float PieceFloor = 0.0f;

    /** The project's pieces for Style (nothing for Propia). */
    void ApplyStyle(EFactoryRailStyle Style);
    /** A rail from From to To standing on a floor at Z, its outside towards Outside; bFirstPost: a post at From too. */
    void Place(UInstancedStaticMeshComponent* Rails, UInstancedStaticMeshComponent* Posts, FVector2D From, FVector2D To,
               FVector2D Outside, bool bFirstPost, float Z) const;
};

/**
 * A rectangular steel platform built from pieces (Scripts/author_plataforma_y_barandas.py): a leg with its braces at
 * each corner, beams along the sides between them and a deck plate filling the middle. Its sides are MinX/MaxX/MinY/
 * MaxY (actor space, cm); in the viewport each side has a diamond handle (drag it and that side moves: the beams and the
 * deck follow, the corners stay corners) and the height handle raises or lowers the deck (the legs stretch, as in the
 * walkways). Each side can carry a rail (bRail...), in the style RailStyle.
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryPlatform : public AFactoryWalkway
{
    GENERATED_BODY()
public:
    AFactoryPlatform();
    UPROPERTY(Category="Platform", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float MinX = -124.0f;
    UPROPERTY(Category="Platform", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float MaxX = 124.0f;
    UPROPERTY(Category="Platform", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float MinY = -124.0f;
    UPROPERTY(Category="Platform", EditAnywhere, BlueprintReadWrite, meta=(Units="Centimeters")) float MaxY = 124.0f;
    UPROPERTY(Category="Platform|Rails", EditAnywhere, BlueprintReadWrite) bool bRailMinX = false;
    UPROPERTY(Category="Platform|Rails", EditAnywhere, BlueprintReadWrite) bool bRailMaxX = false;
    UPROPERTY(Category="Platform|Rails", EditAnywhere, BlueprintReadWrite) bool bRailMinY = false;
    UPROPERTY(Category="Platform|Rails", EditAnywhere, BlueprintReadWrite) bool bRailMaxY = false;
    UPROPERTY(Category="Platform|Rails", EditAnywhere, BlueprintReadWrite) EFactoryRailStyle RailStyle = EFactoryRailStyle::Verde;
    UPROPERTY(Category="Platform|Rails", EditAnywhere, BlueprintReadWrite) FFactoryRailPieces RailPieces;
    /** How far inside the edge the rails stand (cm). */
    UPROPERTY(Category="Platform|Rails", EditAnywhere, BlueprintReadWrite) float RailInset = 12.0f;

    /** Pieces: the +X+Y corner (origin at its outer corner), the leg's column (z from 0, stretched) and foot, a side
     *  beam (along X, origin on the +Y edge, inwards -Y) and the deck plate (centred). Empty: the project's own. */
    UPROPERTY(Category="Platform|Pieces", EditAnywhere, BlueprintReadWrite) TObjectPtr<UStaticMesh> CornerMesh;
    UPROPERTY(Category="Platform|Pieces", EditAnywhere, BlueprintReadWrite) TObjectPtr<UStaticMesh> FootMesh;
    UPROPERTY(Category="Platform|Pieces", EditAnywhere, BlueprintReadWrite) TObjectPtr<UStaticMesh> EdgeMesh;
    UPROPERTY(Category="Platform|Pieces", EditAnywhere, BlueprintReadWrite) float CornerSize = 62.0f;
    UPROPERTY(Category="Platform|Pieces", EditAnywhere, BlueprintReadWrite) float EdgePieceLength = 60.0f;
    UPROPERTY(Category="Platform|Pieces", EditAnywhere, BlueprintReadWrite) float DeckPieceWidth = 120.0f;
    UPROPERTY(Category="Platform|Pieces", EditAnywhere, BlueprintReadWrite) float FootTop = 9.0f;

    UPROPERTY(Category="Platform", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Corners;
    UPROPERTY(Category="Platform", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Feet;
    UPROPERTY(Category="Platform", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Edges;

    UPROPERTY(Category="Platform|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector MinXHandle = FVector::ZeroVector;
    UPROPERTY(Category="Platform|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector MaxXHandle = FVector::ZeroVector;
    UPROPERTY(Category="Platform|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector MinYHandle = FVector::ZeroVector;
    UPROPERTY(Category="Platform|Handles", EditAnywhere, meta=(MakeEditWidget="true")) FVector MaxYHandle = FVector::ZeroVector;
    virtual void OnConstruction(const FTransform& Transform) override;
protected:
    virtual void ApplyHandles() override;
    virtual void BuildPieces() override;
    virtual FString PieceFolder() const override { return TEXT("/Game/FactoryCtyco/Environments/Plataformas/Industrial"); }
    virtual FString PiecePrefix() const override { return TEXT("SM_Plataforma"); }
    virtual FVector2D HeightHandleAt() const override { return FVector2D((MinX + MaxX) / 2, (MinY + MaxY) / 2); }
private:
    FVector Placed[4];
};

/**
 * A free-standing rail along a line: the line's points (Path, a spline; in the viewport select a point to drag it,
 * Alt-drag to add one) are its corners, with a post at each and rail spans between, level at each segment's first
 * point. Its outside is the left of the line's direction (bFlip: the right).
 */
UCLASS(Blueprintable)
class FACTORYCTYCORUNTIME_API AFactoryRailing : public AActor
{
    GENERATED_BODY()
public:
    AFactoryRailing();
    UPROPERTY(Category="Railing", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USplineComponent> Path;
    UPROPERTY(Category="Railing", EditAnywhere, BlueprintReadWrite) EFactoryRailStyle Style = EFactoryRailStyle::Verde;
    UPROPERTY(Category="Railing", EditAnywhere, BlueprintReadWrite) FFactoryRailPieces Pieces;
    UPROPERTY(Category="Railing", EditAnywhere, BlueprintReadWrite) bool bFlip = false;
    /** Joins the last point back to the first. */
    UPROPERTY(Category="Railing", EditAnywhere, BlueprintReadWrite) bool bClosed = false;
    UPROPERTY(Category="Railing", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Rails;
    UPROPERTY(Category="Railing", VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Posts;

    UFUNCTION(Category="Railing", BlueprintCallable) void Rebuild();
    virtual void OnConstruction(const FTransform& Transform) override;
};
