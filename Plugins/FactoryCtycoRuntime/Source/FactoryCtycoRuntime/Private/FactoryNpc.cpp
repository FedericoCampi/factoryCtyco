#include "FactoryNpc.h"
#include "Animation/AnimationAsset.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

AFactoryNpc::AFactoryNpc()
{
    PrimaryActorTick.bCanEverTick = true;
    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);
    Skeletal = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Skeletal"));
    Skeletal->SetupAttachment(Root);
    Skeletal->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
    Body->SetupAttachment(Root);
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    // Sized for someone seated on the floor, facing +Y (feet forward, back behind).
    Blocker = CreateDefaultSubobject<UBoxComponent>(TEXT("Blocker"));
    Blocker->SetupAttachment(Root);
    Blocker->SetBoxExtent(FVector(38, 45, 55));
    Blocker->SetRelativeLocation(FVector(0, 10, 55));
    Blocker->SetCollisionProfileName(TEXT("BlockAllDynamic"));
    Lines = {TEXT("¿Y ella?")};
}

void AFactoryNpc::BeginPlay()
{
    Super::BeginPlay();
    BaseScale = Body->GetRelativeScale3D();
    if (Skeletal->GetSkeletalMeshAsset() && IdleAnimation) Skeletal->PlayAnimation(IdleAnimation, true);
}

void AFactoryNpc::SayLine(int32 Index, float Now)
{
    Line = Index;
    LineShownAt = Now;
    // The gesture of the line (once), then back to the idle loop in Tick.
    if (TalkAnimation && Skeletal->GetSkeletalMeshAsset())
    {
        Skeletal->PlayAnimation(TalkAnimation, false);
        TalkEndsAt = Now + TalkAnimation->GetPlayLength();
    }
    if (LineSounds.IsValidIndex(Index) && LineSounds[Index])
    {
        UGameplayStatics::PlaySoundAtLocation(this, LineSounds[Index], GetActorLocation() + FVector(0, 0, SpeechHeight - 30));
        ++LinesVoiced;
    }
}

void AFactoryNpc::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const float Now = GetWorld()->GetRealTimeSeconds();
    // Without an animated body, the static one breathes: it rises and falls a little.
    if (Body->GetStaticMesh())
        Body->SetRelativeScale3D(BaseScale * FVector(1.0f, 1.0f, 1.0f + .012f * FMath::Sin(GetWorld()->GetTimeSeconds() * 1.7f)));
    const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
    const bool bWasNear = bNear;
    bNear = Player && FVector::Dist2D(Player->GetActorLocation(), GetActorLocation()) <= TalkRadius
        && FMath::Abs(Player->GetActorLocation().Z - GetActorLocation().Z) < 300.0f;
    if (bNear && !bWasNear)
    {
        bTalking = true;
        SayLine(0, Now);
    }
    else if (!bNear && bWasNear) LeftAt = Now;
    if (bNear && Lines.IsValidIndex(Line + 1) && Now - LineShownAt > SecondsPerLine) SayLine(Line + 1, Now);
    if (TalkEndsAt > 0.0f && Now >= TalkEndsAt)
    {
        TalkEndsAt = 0.0f;
        if (IdleAnimation) Skeletal->PlayAnimation(IdleAnimation, true);
    }
    // The bubble fades out for a moment after the player walks away.
    if (!bNear && bTalking && Now - LeftAt > .3f) bTalking = false;
}
