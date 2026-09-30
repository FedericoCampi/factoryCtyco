#include "FactoryMachineSwitch.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/LightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"

static const FName PowerParameter(TEXT("Power"));

AFactoryMachineSwitch::AFactoryMachineSwitch()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickInterval = 0.0f;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Prompt = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Prompt"));
    Prompt->SetupAttachment(RootComponent);
    Prompt->SetAbsolute(false, false, true);
    Prompt->SetRelativeLocation(FVector(0, 0, 70));
    Prompt->SetHorizontalAlignment(EHTA_Center);
    Prompt->SetVerticalAlignment(EVRTA_TextCenter);
    Prompt->SetWorldSize(22.0f);
    Prompt->SetTextRenderColor(FColor(46, 232, 199));
    Prompt->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Prompt->SetHiddenInGame(true);
}

void AFactoryMachineSwitch::BeginPlay()
{
    Super::BeginPlay();
    TArray<AActor*> Targets(PoweredActors);
    if (Machine) Targets.Add(Machine);
    for (AActor* Target : Targets)
    {
        if (!IsValid(Target)) continue;
        TArray<UActorComponent*> Components;
        Target->GetComponents(Components);
        for (UActorComponent* Component : Components)
        {
            if (auto* Light = Cast<ULightComponent>(Component))
            {
                Lights.Add(Light);
                LightIntensity.Add(Light->Intensity);
                continue;
            }
            if (auto* Skeletal = Cast<USkeletalMeshComponent>(Component)) Animated.Add(Skeletal);
            auto* Mesh = Cast<UMeshComponent>(Component);
            if (!Mesh) continue;
            for (int32 Index = 0; Index < Mesh->GetNumMaterials(); ++Index)
            {
                float Unused = 0;
                UMaterialInterface* Material = Mesh->GetMaterial(Index);
                if (Material && Material->GetScalarParameterValue(FHashedMaterialParameterInfo(PowerParameter), Unused))
                    PowerMaterials.Add(Mesh->CreateAndSetMaterialInstanceDynamic(Index));
            }
        }
    }
    bActive = bStartActive;
    Power = bActive ? 1.0f : 0.0f;
    ApplyPower();
}

void AFactoryMachineSwitch::ApplyPower()
{
    for (UMaterialInstanceDynamic* Material : PowerMaterials)
        if (Material) Material->SetScalarParameterValue(PowerParameter, Power);
    for (int32 Index = 0; Index < Lights.Num(); ++Index)
        if (Lights[Index])
        {
            Lights[Index]->SetIntensity(LightIntensity[Index] * Power);
            Lights[Index]->SetVisibility(Power > 0.01f);
        }
    // The animation spins up and winds down with the power instead of snapping.
    for (USkeletalMeshComponent* Skeletal : Animated)
        if (Skeletal) Skeletal->SetPlayRate(Power);
}

void AFactoryMachineSwitch::SetMachineOn(bool bOn) { bActive = bOn; }

bool AFactoryMachineSwitch::InReach(const AActor* User) const
{
    if (!User) return false;
    const FVector Origin = User->GetActorLocation(), Target = GetActorLocation();
    return FVector::DistSquared2D(Origin, Target) <= FMath::Square(InteractionRadius) && FMath::Abs(Origin.Z - Target.Z) < 250.0f;
}

bool AFactoryMachineSwitch::TryInteract(AActor* User)
{
    if (!InReach(User)) return false;
    SetMachineOn(!bActive);
    return true;
}

void AFactoryMachineSwitch::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const float Target = bActive ? 1.0f : 0.0f;
    if (Power != Target)
    {
        Power = FMath::FInterpConstantTo(Power, Target, DeltaSeconds, 1.0f / SpinUpSeconds);
        ApplyPower();
    }
    APlayerController* Player = GetWorld()->GetFirstPlayerController();
    const APawn* Pawn = Player ? Player->GetPawn() : nullptr;
    const bool bNear = Pawn && InReach(Pawn);
    Prompt->SetHiddenInGame(!bNear);
    if (!bNear) return;
    Prompt->SetText(FText::FromString(FString::Printf(TEXT("[E] %s %s"), bActive ? TEXT("APAGAR") : TEXT("ENCENDER"), *MachineName)));
    if (Player->PlayerCameraManager)  // TextRender reads along +X: turn it toward the camera.
        Prompt->SetWorldRotation((Player->PlayerCameraManager->GetCameraLocation() - Prompt->GetComponentLocation()).Rotation());
}
