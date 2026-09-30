#include "FactoryRollDoor.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace { float Smooth(float A) { A = FMath::Clamp(A, 0.0f, 1.0f); return A * A * (3.0f - 2.0f * A); } }

AFactoryRollDoor::AFactoryRollDoor()
{
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Door = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Door"));
    Door->SetupAttachment(RootComponent);
    Door->SetCollisionProfileName(TEXT("NoCollision"));   // the doorway already has an invisible wall for the character
    Door->SetMobility(EComponentMobility::Movable);
    Housing = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Housing"));
    Housing->SetupAttachment(RootComponent);
    Housing->SetRelativeLocation(FVector(43, 0, 24));
    Housing->SetCollisionProfileName(TEXT("NoCollision"));
    Button = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Button"));
    Button->SetupAttachment(RootComponent);
    Button->SetRelativeLocation(FVector(26, -200, -119));
    Button->SetCollisionProfileName(TEXT("BlockAll"));
    Prompt = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Prompt"));
    Prompt->SetupAttachment(Button);
    Prompt->SetRelativeLocation(FVector(40, 0, 45));
    Prompt->SetHorizontalAlignment(EHTA_Center);
    Prompt->SetVerticalAlignment(EVRTA_TextCenter);
    Prompt->SetWorldSize(18.0f);
    Prompt->SetTextRenderColor(FColor(46, 232, 199));
    Prompt->SetText(FText::GetEmpty());  // filled in play; empty, nothing shows in the editor
    Prompt->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Prompt->SetHiddenInGame(true);
}

void AFactoryRollDoor::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    Openness = bWantOpen ? 1.0f : 0.0f;
    PlaceDoor();
}

void AFactoryRollDoor::BeginPlay()
{
    Super::BeginPlay();
    Openness = bWantOpen ? 1.0f : 0.0f;
    const int32 Slot = Button->GetMaterialIndex(TEXT("M_PortonLuz"));
    if (Slot != INDEX_NONE) LightMaterial = Button->CreateAndSetMaterialInstanceDynamic(Slot);
    PlaceDoor();
}

void AFactoryRollDoor::PlaceDoor()
{
    // Rolled up, the curtain is a thin band under its box (it shrinks toward its top edge).
    Door->SetRelativeScale3D(FVector(1, 1, FMath::Lerp(1.0f, 0.04f, Smooth(Openness))));
    if (LightMaterial) LightMaterial->SetScalarParameterValue(TEXT("Encendido"), Openness > 0.5f ? 1.0f : 0.0f);
}

void AFactoryRollDoor::GetCrossLine(FVector& OutA, FVector& OutB) const
{
    OutA = GetActorTransform().TransformPosition(FVector(0, -DoorWidth / 2, -DoorHeight));
    OutB = GetActorTransform().TransformPosition(FVector(0, DoorWidth / 2, -DoorHeight));
}

bool AFactoryRollDoor::InReach(const AActor* User) const
{
    if (!User) return false;
    const FVector Target = Button->GetComponentLocation();
    return FVector::DistSquared2D(User->GetActorLocation(), Target) <= FMath::Square(InteractionRadius)
        && FMath::Abs(User->GetActorLocation().Z - Target.Z) < 250.0f;
}

void AFactoryRollDoor::SetOpen(bool bOpen)
{
    if (!bOpen && bVehicleUnder) return;   // never onto a truck
    if (bOpen == bWantOpen) return;
    bWantOpen = bOpen;
    if (MoveSound) UGameplayStatics::PlaySoundAtLocation(this, MoveSound, GetActorLocation());
}

bool AFactoryRollDoor::TryInteract(AActor* User)
{
    if (!InReach(User)) return false;
    SetOpen(!bWantOpen);
    return true;
}

void AFactoryRollDoor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const float Target = bWantOpen ? 1.0f : 0.0f;
    if (Openness != Target)
    {
        Openness = FMath::FInterpConstantTo(Openness, Target, DeltaSeconds, 1.0f / OpenSeconds);
        PlaceDoor();
    }
    APlayerController* Player = GetWorld()->GetFirstPlayerController();
    const APawn* Pawn = Player ? Player->GetPawn() : nullptr;
    const bool bNear = InReach(Pawn);
    Prompt->SetHiddenInGame(!bNear);
    if (!bNear) return;
    Prompt->SetText(FText::FromString(bVehicleUnder && bWantOpen ? TEXT("CAMIÓN PASANDO")
        : bWantOpen ? TEXT("[E] CERRAR PORTÓN") : TEXT("[E] ABRIR PORTÓN")));
    if (Player->PlayerCameraManager)  // TextRender reads along +X: turn it toward the camera
        Prompt->SetWorldRotation((Player->PlayerCameraManager->GetCameraLocation() - Prompt->GetComponentLocation()).Rotation());
}
