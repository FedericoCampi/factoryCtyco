#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "Subsystems/WorldSubsystem.h"
#include "FactoryEconomy.generated.h"

/** Prices of the factory (Project Settings > Game > Economía de la fábrica; saved in Config/DefaultGame.ini). */
UCLASS(Config=Game, DefaultConfig, meta=(DisplayName="Economía de la fábrica"))
class FACTORYCTYCORUNTIME_API UFactoryEconomySettings : public UDeveloperSettings
{
    GENERATED_BODY()
public:
    UFactoryEconomySettings();
    virtual FName GetCategoryName() const override { return TEXT("Game"); }
    /** Money when a game starts. */
    UPROPERTY(Config, EditAnywhere, Category="Economía", meta=(ClampMin="0")) int32 StartingMoney = 0;
    /** Paid for each package delivered (when its truck leaves). */
    UPROPERTY(Config, EditAnywhere, Category="Economía", meta=(ClampMin="0")) int32 PricePerPackage = 60;
    /** What hiring each job costs (job name as in the hire point, e.g. Barrera). */
    UPROPERTY(Config, EditAnywhere, Category="Economía") TMap<FName, int32> HireCosts;
};

/** One change of money, for the HUD's "+$60" / "-$800" pops. */
USTRUCT(BlueprintType)
struct FFactoryMoneyChange
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="Economía") int32 Amount = 0;
    UPROPERTY(BlueprintReadOnly, Category="Economía") FString Reason;
    /** Real time when it happened. */
    UPROPERTY(BlueprintReadOnly, Category="Economía") float At = 0.0f;
};

/**
 * The factory's money: it starts at StartingMoney, deliveries pay PricePerPackage each and hiring costs HireCosts.
 * Spend refuses (and changes nothing) when there is not enough. The HUD shows it at the top left.
 */
UCLASS()
class FACTORYCTYCORUNTIME_API UFactoryEconomySubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintPure, Category="Economía", meta=(WorldContext="Context")) static UFactoryEconomySubsystem* Get(const UObject* Context);
    UFUNCTION(BlueprintPure, Category="Economía") int32 GetMoney() const { return Money; }
    UFUNCTION(BlueprintPure, Category="Economía") bool CanAfford(int32 Amount) const { return Amount <= Money; }
    /** Takes Amount if there is enough; returns whether it was paid. */
    UFUNCTION(BlueprintCallable, Category="Economía") bool Spend(int32 Amount, const FString& Reason);
    UFUNCTION(BlueprintCallable, Category="Economía") void Earn(int32 Amount, const FString& Reason);
    /** What hiring Role costs (0 when it has no price). */
    UFUNCTION(BlueprintPure, Category="Economía") int32 GetHireCost(FName Role) const;
    /** The latest changes, newest last (the HUD shows the recent ones). */
    const TArray<FFactoryMoneyChange>& GetChanges() const { return Changes; }
    /** "$ 1.500" (dots for thousands). */
    static FString Format(int32 Amount);
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
private:
    UPROPERTY() int32 Money = 0;
    UPROPERTY() TArray<FFactoryMoneyChange> Changes;
    void Record(int32 Amount, const FString& Reason);
};
