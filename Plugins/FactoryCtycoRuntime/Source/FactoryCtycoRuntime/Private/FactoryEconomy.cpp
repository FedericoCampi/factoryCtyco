#include "FactoryEconomy.h"
#include "Engine/World.h"

UFactoryEconomySettings::UFactoryEconomySettings()
{
    HireCosts.Add(TEXT("Barrera"), 800);
}

UFactoryEconomySubsystem* UFactoryEconomySubsystem::Get(const UObject* Context)
{
    const UWorld* World = Context ? Context->GetWorld() : nullptr;
    return World ? World->GetSubsystem<UFactoryEconomySubsystem>() : nullptr;
}

void UFactoryEconomySubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);
    Money = GetDefault<UFactoryEconomySettings>()->StartingMoney;
    Changes.Reset();
}

void UFactoryEconomySubsystem::Record(int32 Amount, const FString& Reason)
{
    FFactoryMoneyChange Change;
    Change.Amount = Amount;
    Change.Reason = Reason;
    Change.At = GetWorld()->GetRealTimeSeconds();
    Changes.Add(Change);
    if (Changes.Num() > 12) Changes.RemoveAt(0);
}

bool UFactoryEconomySubsystem::Spend(int32 Amount, const FString& Reason)
{
    if (Amount < 0 || Amount > Money) return false;
    if (Amount == 0) return true;
    Money -= Amount;
    Record(-Amount, Reason);
    return true;
}

void UFactoryEconomySubsystem::Earn(int32 Amount, const FString& Reason)
{
    if (Amount <= 0) return;
    Money += Amount;
    Record(Amount, Reason);
}

int32 UFactoryEconomySubsystem::GetHireCost(FName Role) const
{
    const int32* Cost = GetDefault<UFactoryEconomySettings>()->HireCosts.Find(Role);
    return Cost ? *Cost : 0;
}

FString UFactoryEconomySubsystem::Format(int32 Amount)
{
    FString Digits = FString::FromInt(FMath::Abs(Amount));
    for (int32 At = Digits.Len() - 3; At > 0; At -= 3) Digits.InsertAt(At, TEXT("."));
    return FString(Amount < 0 ? TEXT("-$ ") : TEXT("$ ")) + Digits;
}
