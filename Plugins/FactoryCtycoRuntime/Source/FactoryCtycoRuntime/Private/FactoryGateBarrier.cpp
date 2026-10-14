#include "FactoryGateBarrier.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

AFactoryGateBarrier::AFactoryGateBarrier()
{
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Booth = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Booth"));
    Booth->SetupAttachment(RootComponent);
    Booth->SetCollisionProfileName(TEXT("BlockAll"));
    Booth->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);  // the camera looks in from above
    Roof = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Roof"));
    Roof->SetupAttachment(Booth);
    Roof->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Post = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Post"));
    Post->SetupAttachment(RootComponent);
    Post->SetRelativeLocationAndRotation(FVector(-20, 120, 0), FRotator(0, 90, 0));
    Post->SetCollisionProfileName(TEXT("BlockAll"));
    Arm = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Arm"));
    Arm->SetupAttachment(Post);
    Arm->SetRelativeLocation(FVector(0, 0, 109));
    Arm->SetMobility(EComponentMobility::Movable);
    Arm->SetCollisionProfileName(TEXT("BlockAll"));   // the character does not walk through it (08/10)
    Arm->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
    Prompt = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Prompt"));
    Prompt->SetupAttachment(Booth);
    Prompt->SetRelativeLocation(FVector(0, 0, 200));
    Prompt->SetHorizontalAlignment(EHTA_Center);
    Prompt->SetVerticalAlignment(EVRTA_TextCenter);
    Prompt->SetWorldSize(18.0f);
    Prompt->SetTextRenderColor(FColor(46, 232, 199));
    Prompt->SetText(FText::GetEmpty());  // filled in play; empty, nothing shows in the editor
    Prompt->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Prompt->SetHiddenInGame(true);
}

void AFactoryGateBarrier::BeginPlay()
{
    Super::BeginPlay();
    ArmRest = Arm->GetRelativeRotation().Quaternion();
    Openness = bWantOpen ? 1.0f : 0.0f;
    PlaceArm();
}

bool AFactoryGateBarrier::IsInside(const AActor* User) const
{
    if (!User) return false;
    const FVector Local = Booth->GetComponentTransform().InverseTransformPosition(User->GetActorLocation()) - FVector(0, 0, InsideExtent.Z);
    return FMath::Abs(Local.X) <= InsideExtent.X && FMath::Abs(Local.Y) <= InsideExtent.Y && FMath::Abs(Local.Z) <= InsideExtent.Z;
}

void AFactoryGateBarrier::SetOpen(bool bOpen)
{
    if (!bOpen && bVehicleUnder) return;  // never onto a vehicle
    if (bOpen == bWantOpen) return;
    bWantOpen = bOpen;
    if (MoveSound) UGameplayStatics::PlaySoundAtLocation(this, MoveSound, Post->GetComponentLocation());
}

bool AFactoryGateBarrier::TryInteract(AActor* User)
{
    if (!IsInside(User)) return false;
    SetOpen(!bWantOpen);
    return true;
}

void AFactoryGateBarrier::GetArmLine(FVector& OutPivot, FVector& OutTip) const
{
    const FTransform Down = FTransform(ArmRest, Arm->GetRelativeLocation()) * Post->GetComponentTransform();
    OutPivot = Down.GetLocation();
    OutTip = Down.TransformPosition(FVector(ArmLength, 0, 0));
}

void AFactoryGateBarrier::PlaceArm()
{
    // Eased so it starts and stops softly; it rises about its own Y (pitch lifts the +X tip).
    const float Eased = FMath::InterpEaseInOut(0.0f, 1.0f, Openness, 2.0f);
    Arm->SetRelativeRotation(ArmRest * FRotator(RaisedAngle * Eased, 0, 0).Quaternion());
}

void AFactoryGateBarrier::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const float Target = bWantOpen ? 1.0f : 0.0f;
    if (Openness != Target)
    {
        Openness = FMath::FInterpConstantTo(Openness, Target, DeltaSeconds, 1.0f / RaiseSeconds);
        PlaceArm();
    }
    APlayerController* Player = GetWorld()->GetFirstPlayerController();
    const APawn* Pawn = Player ? Player->GetPawn() : nullptr;
    const bool bInside = IsInside(Pawn);
    Roof->SetHiddenInGame(bInside);
    Prompt->SetHiddenInGame(!bInside);
    if (bInside)
    {
        const TCHAR* Action = bWantOpen ? (bVehicleUnder ? TEXT("CAMION PASANDO") : TEXT("[E] BAJAR BARRERA")) : TEXT("[E] LEVANTAR BARRERA");
        Prompt->SetText(FText::FromString(Action));
        if (Player->PlayerCameraManager)  // TextRender reads along +X: turn it toward the camera
            Prompt->SetWorldRotation((Player->PlayerCameraManager->GetCameraLocation() - Prompt->GetComponentLocation()).Rotation());
    }
}
