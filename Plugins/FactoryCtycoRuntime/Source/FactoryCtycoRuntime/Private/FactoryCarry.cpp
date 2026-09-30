#include "FactoryCarry.h"
#include "RobotLocomotionComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

AFactoryLooseBox::AFactoryLooseBox()
{
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
    RootComponent = Mesh;
    Mesh->SetMobility(EComponentMobility::Movable);
    Mesh->SetCollisionProfileName(TEXT("BlockAllDynamic"));
}

UFactoryCarryComponent::UFactoryCarryComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;  // after the animation has posed the hands
}

void UFactoryCarryComponent::SetCarrying(bool bCarrying) const
{
    if (auto* Locomotion = GetOwner()->FindComponentByClass<URobotLocomotionComponent>()) Locomotion->bCarrying = bCarrying;
}

void UFactoryCarryComponent::Play(bool bPickup)
{
    // The component is added at run time: load the default sounds on first use.
    if (!PickupSound) PickupSound = LoadObject<USoundBase>(nullptr, TEXT("/Game/FactoryCtyco/Audio/S_CajaAgarrar.S_CajaAgarrar"));
    if (!DropSound) DropSound = LoadObject<USoundBase>(nullptr, TEXT("/Game/FactoryCtyco/Audio/S_CajaSoltar.S_CajaSoltar"));
    if (USoundBase* Sound = bPickup ? PickupSound.Get() : DropSound.Get())
        UGameplayStatics::PlaySoundAtLocation(this, Sound, GetOwner()->GetActorLocation());
}

bool UFactoryCarryComponent::Take(UStaticMesh* BoxMesh)
{
    if (HeldBox || !BoxMesh) return false;
    HeldBox = NewObject<UStaticMeshComponent>(GetOwner(), TEXT("HeldBox"));
    HeldBox->SetStaticMesh(BoxMesh);
    HeldBox->SetMobility(EComponentMobility::Movable);
    HeldBox->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    HeldBox->SetUsingAbsoluteLocation(true);
    HeldBox->SetUsingAbsoluteRotation(true);
    HeldBox->SetupAttachment(GetOwner()->GetRootComponent());
    HeldBox->RegisterComponent();
    SetCarrying(true);
    PlaceHeldBox();
    Play(true);
    return true;
}

UStaticMesh* UFactoryCarryComponent::Release(FTransform& OutWorld)
{
    if (!HeldBox) return nullptr;
    UStaticMesh* Mesh = HeldBox->GetStaticMesh();
    OutWorld = HeldBox->GetComponentTransform();
    HeldBox->DestroyComponent();
    HeldBox = nullptr;
    SetCarrying(false);
    Play(false);
    return Mesh;
}

bool UFactoryCarryComponent::Drop()
{
    if (!HeldBox) return false;
    AActor* Owner = GetOwner();
    const FVector Forward = FRotator(0, Owner->GetActorRotation().Yaw, 0).Vector();
    const FVector Above = Owner->GetActorLocation() + Forward * 60.0f;
    // Rest it on whatever floor is in front (the character's capsule is ignored).
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(DropBox), false, Owner);
    FVector Location = Above - FVector(0, 0, 90);
    if (GetWorld()->LineTraceSingleByChannel(Hit, Above, Above - FVector(0, 0, 400), ECC_Visibility, Params)) Location = Hit.ImpactPoint;
    FActorSpawnParameters Spawn;
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if (auto* Loose = GetWorld()->SpawnActor<AFactoryLooseBox>(Location, FRotator(0, Owner->GetActorRotation().Yaw, 0), Spawn))
        Loose->Mesh->SetStaticMesh(HeldBox->GetStaticMesh());
    HeldBox->DestroyComponent();
    HeldBox = nullptr;
    SetCarrying(false);
    Play(false);
    return true;
}

AFactoryLooseBox* UFactoryCarryComponent::NearestLoose(float& OutDistanceSquared) const
{
    AFactoryLooseBox* Best = nullptr;
    OutDistanceSquared = FMath::Square(PickupRadius);
    const FVector Origin = GetOwner()->GetActorLocation();
    for (TActorIterator<AFactoryLooseBox> It(GetWorld()); It; ++It)
    {
        const float Distance = FVector::DistSquared2D(Origin, It->GetActorLocation());
        if (Distance <= OutDistanceSquared && FMath::Abs(Origin.Z - It->GetActorLocation().Z) < 200.0f)
        {
            OutDistanceSquared = Distance;
            Best = *It;
        }
    }
    return Best;
}

bool UFactoryCarryComponent::PickLoose()
{
    float Distance = 0.0f;
    AFactoryLooseBox* Loose = HeldBox ? nullptr : NearestLoose(Distance);
    if (!Loose || !Take(Loose->Mesh->GetStaticMesh())) return false;
    Loose->Destroy();
    return true;
}

void UFactoryCarryComponent::PlaceHeldBox() const
{
    const auto* Character = Cast<ACharacter>(GetOwner());
    const USkeletalMeshComponent* Body = Character ? Character->GetMesh() : nullptr;
    if (!HeldBox || !Body) return;
    const FVector Forward = FRotator(0, GetOwner()->GetActorRotation().Yaw, 0).Vector();
    const FVector Centre = (Body->GetBoneLocation(LeftHand) + Body->GetBoneLocation(RightHand)) / 2 + Forward * ForwardOffset;
    // The box mesh has its pivot at the bottom centre.
    const float HalfHeight = HeldBox->GetStaticMesh() ? HeldBox->GetStaticMesh()->GetBounds().BoxExtent.Z : 16.0f;
    HeldBox->SetWorldLocationAndRotation(Centre - FVector(0, 0, HalfHeight), FRotator(0, GetOwner()->GetActorRotation().Yaw, 0));
}

void UFactoryCarryComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    PlaceHeldBox();
    // "[E] AGARRAR CAJA" over the nearest loose box.
    float Distance = 0.0f;
    AFactoryLooseBox* Loose = HeldBox ? nullptr : NearestLoose(Distance);
    if (Loose && !LoosePrompt)
    {
        LoosePrompt = NewObject<UTextRenderComponent>(GetOwner(), TEXT("LooseBoxPrompt"));
        LoosePrompt->SetUsingAbsoluteLocation(true);
        LoosePrompt->SetUsingAbsoluteRotation(true);
        LoosePrompt->SetHorizontalAlignment(EHTA_Center);
        LoosePrompt->SetVerticalAlignment(EVRTA_TextCenter);
        LoosePrompt->SetWorldSize(18.0f);
        LoosePrompt->SetTextRenderColor(FColor(46, 232, 199));
        LoosePrompt->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        LoosePrompt->SetText(FText::FromString(TEXT("[E] AGARRAR CAJA")));
        LoosePrompt->SetupAttachment(GetOwner()->GetRootComponent());
        LoosePrompt->RegisterComponent();
    }
    if (!LoosePrompt) return;
    LoosePrompt->SetHiddenInGame(!Loose);
    if (!Loose) return;
    LoosePrompt->SetWorldLocation(Loose->GetActorLocation() + FVector(0, 0, 70));
    if (const APlayerController* Player = GetWorld()->GetFirstPlayerController())
        if (Player->PlayerCameraManager)
            LoosePrompt->SetWorldRotation((Player->PlayerCameraManager->GetCameraLocation() - LoosePrompt->GetComponentLocation()).Rotation());
}

void UFactoryCarryComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if (HeldBox) HeldBox->DestroyComponent();
    if (LoosePrompt) LoosePrompt->DestroyComponent();
    Super::EndPlay(Reason);
}
