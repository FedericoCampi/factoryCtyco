#include "FactoryMission.h"
#include "FactoryEconomy.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FactoryLoadingBelt.h"
#include "FactoryVehiclePath.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

UFactoryMissionSubsystem* UFactoryMissionSubsystem::Get(const UObject* Context)
{
    const UWorld* World = Context ? Context->GetWorld() : nullptr;
    return World ? World->GetSubsystem<UFactoryMissionSubsystem>() : nullptr;
}

void UFactoryMissionSubsystem::AddDelivered(int32 Packages)
{
    if (Packages <= 0) return;
    Delivered += Packages;
    if (UFactoryEconomySubsystem* Economy = UFactoryEconomySubsystem::Get(this))
        Economy->Earn(Packages * GetDefault<UFactoryEconomySettings>()->PricePerPackage,
                      FString::Printf(TEXT("%d paquetes entregados"), Packages));
    if (bCompleted || Delivered < Goal) return;
    bCompleted = true;
    CompletedAt = GetWorld()->GetTimeSeconds();
    if (!CompleteSound) CompleteSound = LoadObject<USoundBase>(nullptr, TEXT("/Game/FactoryCtyco/Audio/S_MisionCompleta.S_MisionCompleta"));
    if (CompleteSound) UGameplayStatics::PlaySound2D(this, CompleteSound);
}

const FName UFactoryUnlockSubsystem::LockedTag(TEXT("Bloqueado"));
const FName UFactoryUnlockSubsystem::FillerTag(TEXT("Relleno"));

bool UFactoryUnlockSubsystem::IsLocked(const AActor* Actor)
{
    return Actor && Actor->ActorHasTag(LockedTag);
}

UFactoryUnlockSubsystem* UFactoryUnlockSubsystem::Get(const UObject* Context)
{
    const UWorld* World = Context ? Context->GetWorld() : nullptr;
    return World ? World->GetSubsystem<UFactoryUnlockSubsystem>() : nullptr;
}

void UFactoryUnlockSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);
    for (TActorIterator<AActor> It(&InWorld); It; ++It)
        if (IsLocked(*It))
        {
            It->SetActorHiddenInGame(true);
            It->SetActorEnableCollision(false);
            It->SetActorTickEnabled(false);
        }
}

int32 UFactoryUnlockSubsystem::Unlock(FName Group)
{
    int32 Changed = 0;
    for (TActorIterator<AActor> It(GetWorld()); It; ++It)
    {
        if (!It->ActorHasTag(Group)) continue;
        if (It->ActorHasTag(LockedTag))
        {
            It->Tags.Remove(LockedTag);
            It->SetActorHiddenInGame(false);
            It->SetActorEnableCollision(true);
            It->SetActorTickEnabled(true);
            ++Changed;
        }
        else if (It->ActorHasTag(FillerTag))
        {
            It->Destroy();
            ++Changed;
        }
    }
    // Belts relink and trucks look for their stops again, now with the new pieces.
    for (TActorIterator<AFactoryLoadingBelt> It(GetWorld()); It; ++It) It->RefreshLinks();
    for (TActorIterator<AFactoryVehiclePath> It(GetWorld()); It; ++It) It->RefreshStops();
    return Changed;
}
