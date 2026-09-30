#include "FactoryHover.h"
#include "FactoryCameraComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "FactoryDemo.h"
#include "FactoryDispatchBelt.h"
#include "FactoryGateBarrier.h"
#include "FactoryGuide.h"
#include "GameFramework/Character.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

UFactoryHoverComponent::UFactoryHoverComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
}

void UFactoryHoverComponent::BeginPlay()
{
    Super::BeginPlay();
    auto* Camera = GetOwner()->FindComponentByClass<UCameraComponent>();
    auto* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/FactoryCtyco/UI/M_ContornoClic.M_ContornoClic"));
    if (!Camera || !Base) { SetComponentTickEnabled(false); return; }
    Outline = UMaterialInstanceDynamic::Create(Base, this);
    Outline->SetVectorParameterValue(TEXT("Color"), OutlineColor);
    Outline->SetScalarParameterValue(TEXT("Ancho"), OutlineWidth);
    Camera->PostProcessSettings.AddBlendable(Outline, 1.0f);
}

void UFactoryHoverComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    SetLit({});
    Super::EndPlay(Reason);
}

AActor* UFactoryHoverComponent::FindClickable(TArray<UPrimitiveComponent*>& Parts) const
{
    const auto* Pawn = Cast<APawn>(GetOwner());
    APlayerController* Player = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
    float MouseX = 0, MouseY = 0;
    if (!Player || !Player->GetMousePosition(MouseX, MouseY)) return nullptr;
    // Nothing in the world is clickable while the intro covers the screen or while building.
    if (const AFactoryGuide* Guide = AFactoryGuide::Find(GetWorld()); Guide && Guide->IsCovering()) return nullptr;
    if (const auto* Demo = Pawn->FindComponentByClass<UFactoryDemoComponent>(); Demo && Demo->bBuilding) return nullptr;
    // Same order as a click (UFactoryDemoComponent::Click): characters first, then what the cursor hits.
    if (const auto* Camera = Pawn->FindComponentByClass<UFactoryCameraComponent>())
        if (ACharacter* Character = Camera->CharacterAtScreen(FVector2D(MouseX, MouseY)))
        {
            if (Character->GetMesh()) Parts.Add(Character->GetMesh());
            return Character;
        }
    FHitResult Hit;
    if (!Player->GetHitResultUnderCursor(ECC_Visibility, false, Hit) || !Hit.GetActor()) return nullptr;
    if (auto* Barrier = Cast<AFactoryGateBarrier>(Hit.GetActor()))
    {
        Barrier->GetComponents<UPrimitiveComponent>(Parts);
        return Barrier;
    }
    for (TActorIterator<AFactoryDispatchBelt> It(GetWorld()); It; ++It)
        if (It->bFull && It->Sign && Hit.GetComponent() == It->Sign)
        {
            Parts.Add(It->Sign);
            return *It;
        }
    return nullptr;
}

void UFactoryHoverComponent::SetLit(const TArray<UPrimitiveComponent*>& Parts)
{
    for (const TWeakObjectPtr<UPrimitiveComponent>& Part : Lit)
        if (Part.IsValid() && !Parts.Contains(Part.Get())) Part->SetRenderCustomDepth(false);
    Lit.Reset();
    for (UPrimitiveComponent* Part : Parts)
    {
        // Only what draws (not collision boxes or triggers).
        if (!Part || !Part->IsVisible() || Part->bHiddenInGame) continue;
        Part->SetRenderCustomDepth(true);
        Lit.Add(Part);
    }
}

void UFactoryHoverComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    TArray<UPrimitiveComponent*> Parts;
    AActor* Target = FindClickable(Parts);
    if (Target != Hovered.Get() || Parts.Num() != Lit.Num()) SetLit(Parts);
    Hovered = Target;
    const auto* Pawn = Cast<APawn>(GetOwner());
    if (APlayerController* Player = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr)
        Player->CurrentMouseCursor = Target ? EMouseCursor::Hand : EMouseCursor::Default;
}
