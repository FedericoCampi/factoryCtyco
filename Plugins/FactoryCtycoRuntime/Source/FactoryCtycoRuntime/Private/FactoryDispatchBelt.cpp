#include "FactoryDispatchBelt.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "FactoryCarry.h"
#include "FactoryMission.h"
#include "Kismet/GameplayStatics.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"

static const FName RollerSlot(TEXT("M_Rodillo"));
static const FName ButtonSlot(TEXT("M_Boton"));

AFactoryDispatchBelt::AFactoryDispatchBelt()
{
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Sign = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Sign"));
    Sign->SetupAttachment(RootComponent);
    Sign->SetRelativeLocation(SignLocation);
    Sign->SetCollisionProfileName(TEXT("NoCollision"));
    Sign->SetCollisionEnabled(ECollisionEnabled::QueryOnly);  // only for clicks under the cursor
    Sign->SetCollisionResponseToAllChannels(ECR_Ignore);
    Sign->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    Sign->SetHiddenInGame(true);
    SignText = CreateDefaultSubobject<UTextRenderComponent>(TEXT("SignText"));
    SignText->SetupAttachment(Sign);
    SignText->SetRelativeLocation(FVector(5, 0, 3));
    SignText->SetHorizontalAlignment(EHTA_Center);
    SignText->SetVerticalAlignment(EVRTA_TextCenter);
    SignText->SetWorldSize(16.0f);
    SignText->SetTextRenderColor(FColor::White);
    SignText->SetText(FText::FromString(TEXT("CINTA LLENA")));
    SignText->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    SignText->SetHiddenInGame(true);
    BoxPrompt = CreateDefaultSubobject<UTextRenderComponent>(TEXT("BoxPrompt"));
    BoxPrompt->SetupAttachment(RootComponent);
    BoxPrompt->SetHorizontalAlignment(EHTA_Center);
    BoxPrompt->SetVerticalAlignment(EVRTA_TextCenter);
    BoxPrompt->SetWorldSize(18.0f);
    BoxPrompt->SetTextRenderColor(FColor(46, 232, 199));
    BoxPrompt->SetText(FText::GetEmpty());  // set in play: an empty text is not drawn in the editor
    BoxPrompt->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    BoxPrompt->SetHiddenInGame(true);
}


void AFactoryDispatchBelt::BeginPlay()
{
    Super::BeginPlay();
    SinceLastBox = SecondsBetweenBoxes;  // the first box comes out right away
    BoxPrompt->SetText(FText::FromString(TEXT("[E] AGARRAR CAJA")));
    // Boxes and sign live in the machine's space: if this actor was moved off the machine, snap it back.
    if (GetAttachParentActor() && !RootComponent->GetRelativeTransform().Equals(FTransform::Identity))
        RootComponent->SetRelativeTransform(FTransform::Identity);
    for (TActorIterator<AFactoryBeltButton> It(GetWorld()); It; ++It)
        if (It->Belt == this) { Button = *It; break; }
    Sign->SetRelativeLocation(SignLocation);
    Sign->SetRelativeScale3D(FVector(KINDA_SMALL_NUMBER));
    // The rollers belong to the machine this belt is attached to.
    if (AActor* Machine = GetAttachParentActor())
        if (auto* Mesh = Machine->FindComponentByClass<UStaticMeshComponent>())
        {
            const int32 Slot = Mesh->GetMaterialIndex(RollerSlot);
            if (Slot != INDEX_NONE) RollerMaterial = Mesh->CreateAndSetMaterialInstanceDynamic(Slot);
        }
    if (Button && Button->Panel)
    {
        const int32 Slot = Button->Panel->GetMaterialIndex(ButtonSlot);
        if (Slot != INDEX_NONE) ButtonMaterial = Button->Panel->CreateAndSetMaterialInstanceDynamic(Slot);
    }
    ApplyState();
}

void AFactoryDispatchBelt::ApplyState()
{
    if (RollerMaterial) RollerMaterial->SetScalarParameterValue(TEXT("Velocidad"), bActive ? RollerSpeed : 0.0f);
    if (ButtonMaterial) ButtonMaterial->SetScalarParameterValue(TEXT("Encendido"), bActive ? 1.0f : 0.0f);
}

void AFactoryDispatchBelt::SetBeltOn(bool bOn)
{
    const bool bWas = bActive;
    bActive = bOn && !bFull;
    ApplyState();
    if (bActive != bWas)
        if (USoundBase* Sound = bActive ? OnSound : OffSound) UGameplayStatics::PlaySoundAtLocation(this, Sound, GetPanelLocation());
}

int32 AFactoryDispatchBelt::GetLaneCount() const
{
    // Box centres stay half a box inside the rails; lanes are BoxSpacing apart.
    return FMath::Max(1, FMath::FloorToInt((2.0f * BedHalfWidth - BoxSpacing) / FMath::Max(BoxSpacing, 1.0f)) + 1);
}

int32 AFactoryDispatchBelt::GetCapacity() const
{
    return GetLaneCount() * (FMath::FloorToInt(FVector::Dist(Start, End) / FMath::Max(BoxSpacing, 1.0f)) + 1);
}

float AFactoryDispatchBelt::LaneCentre(int32 Lane) const
{
    return (Lane - (GetLaneCount() - 1) / 2.0f) * BoxSpacing;
}

bool AFactoryDispatchBelt::FindFreeSide(float& OutSide) const
{
    // Box centres stay half a box inside the rails. Take away the room of every box still at the
    // entrance and pick a random point in what is left (longer free stretches are likelier).
    const float Half = FMath::Max(BedHalfWidth - BoxSpacing * 0.5f, 0.0f);
    TArray<FVector2f> Taken;
    for (int32 Index = 0; Index < Boxes.Num(); ++Index)
        if (Travelled[Index] < BoxSpacing) Taken.Add(FVector2f(Lateral[Index] - SameLane(), Lateral[Index] + SameLane()));
    Taken.Sort([](const FVector2f& A, const FVector2f& B) { return A.X < B.X; });
    TArray<FVector2f> Free;
    float Cursor = -Half;
    for (const FVector2f& Span : Taken)
    {
        if (Span.X >= Cursor && Cursor <= Half) Free.Add(FVector2f(Cursor, FMath::Min(Span.X, Half)));
        Cursor = FMath::Max(Cursor, Span.Y);
    }
    if (Cursor <= Half) Free.Add(FVector2f(Cursor, Half));
    if (Free.IsEmpty()) return false;
    float Total = 0.0f;
    for (const FVector2f& Span : Free) Total += Span.Y - Span.X + 1.0f;   // +1: a single free point counts too
    float Pick = FMath::FRandRange(0.0f, Total);
    for (const FVector2f& Span : Free)
    {
        const float Size = Span.Y - Span.X + 1.0f;
        if (Pick <= Size) { OutSide = FMath::Min(Span.X + Pick, Span.Y); return true; }
        Pick -= Size;
    }
    OutSide = Free.Last().Y;
    return true;
}

int32 AFactoryDispatchBelt::NearestBox(const AActor* User, double& OutDistanceSquared) const
{
    int32 Best = INDEX_NONE;
    OutDistanceSquared = FMath::Square(TakeRadius);
    if (!User || UFactoryUnlockSubsystem::IsLocked(this)) return Best;
    const FVector Origin = User->GetActorLocation();
    for (int32 Index = 0; Index < Boxes.Num(); ++Index)
    {
        if (!Boxes[Index]) continue;
        const FVector Box = Boxes[Index]->GetComponentLocation();
        const double Distance = FVector::DistSquared2D(Origin, Box);
        if (Distance <= OutDistanceSquared && FMath::Abs(Origin.Z - Box.Z) < 200.0f)
        {
            OutDistanceSquared = Distance;
            Best = Index;
        }
    }
    return Best;
}

UStaticMesh* AFactoryDispatchBelt::TakeBox(int32 Index)
{
    if (!Boxes.IsValidIndex(Index)) return nullptr;
    UStaticMesh* Mesh = Boxes[Index] ? Boxes[Index]->GetStaticMesh().Get() : BoxMesh.Get();
    if (Boxes[Index]) Boxes[Index]->DestroyComponent();
    Boxes.RemoveAt(Index);
    Travelled.RemoveAt(Index);
    Lateral.RemoveAt(Index);
    Motion.RemoveAt(Index);
    ExtraGap.RemoveAt(Index);
    // There is room again: the boxes behind move up and, if it had stopped by itself, the belt restarts.
    bFull = false;
    if (bStoppedWhenFull)
    {
        bStoppedWhenFull = false;
        SetBeltOn(true);
    }
    return Mesh;
}

bool AFactoryDispatchBelt::ClickSign(UPrimitiveComponent* Clicked)
{
    if (!Clicked || Clicked != Sign || !bFull) return false;
    bDetailOpen = !bDetailOpen;
    return true;
}

FVector AFactoryDispatchBelt::GetPanelLocation() const
{
    return Button && Button->Panel ? Button->Panel->GetComponentLocation() : GetActorLocation();
}

bool AFactoryDispatchBelt::InReach(const AActor* User) const
{
    if (!User || !Button || UFactoryUnlockSubsystem::IsLocked(this)) return false;
    const FVector Origin = User->GetActorLocation(), Target = GetPanelLocation();
    return FVector::DistSquared2D(Origin, Target) <= FMath::Square(InteractionRadius) && FMath::Abs(Origin.Z - Target.Z) < 250.0f;
}

bool AFactoryDispatchBelt::TryInteract(AActor* User)
{
    if (UFactoryUnlockSubsystem::IsLocked(this)) return false;
    if (!InReach(User)) return false;
    if (!bFull) SetBeltOn(!bActive);  // full: the red sign already says so
    return true;
}

void AFactoryDispatchBelt::SpawnBox(float SideOffset)
{
    auto* Box = NewObject<UStaticMeshComponent>(this);
    // A labelled box at random (A to D), or the plain one.
    TArray<UStaticMesh*> Labelled;
    for (const TObjectPtr<UStaticMesh>& Variant : BoxVariants) if (Variant) Labelled.Add(Variant.Get());
    Box->SetStaticMesh(Labelled.IsEmpty() ? BoxMesh.Get() : Labelled[FMath::RandRange(0, Labelled.Num() - 1)]);
    Box->SetMobility(EComponentMobility::Movable);
    Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Box->SetupAttachment(RootComponent);
    const FVector Side = FVector::CrossProduct(End - Start, FVector::UpVector).GetSafeNormal();
    FDispatchBoxMotion Rock;
    Rock.RestYaw = Rock.Yaw = FMath::FRandRange(-MaxYawJitter, MaxYawJitter);
    Rock.Phase = FMath::FRandRange(0.0f, 2.0f * PI);
    Box->SetRelativeLocationAndRotation(Start + Side * SideOffset, FRotator(0, Rock.Yaw, 0));
    Box->RegisterComponent();
    Boxes.Add(Box);
    Travelled.Add(0.0f);
    Lateral.Add(SideOffset);
    Motion.Add(Rock);
    ExtraGap.Add(FMath::FRandRange(0.0f, GapJitter));
    SinceLastBox = 0.0f;
}

void AFactoryDispatchBelt::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (UFactoryUnlockSubsystem::IsLocked(this)) return;   // not built yet
    APlayerController* Player = GetWorld()->GetFirstPlayerController();
    const APawn* Pawn = Player ? Player->GetPawn() : nullptr;
    UTextRenderComponent* Prompt = Button ? Button->Prompt.Get() : nullptr;
    bool bNear = Prompt && Pawn && InReach(Pawn) && !bFull;
    if (bNear)  // only the nearest panel shows its prompt, as E only reaches that one
    {
        const double Mine = FVector::DistSquared2D(Pawn->GetActorLocation(), GetPanelLocation());
        for (TActorIterator<AFactoryDispatchBelt> It(GetWorld()); It; ++It)
            if (*It != this && It->InReach(Pawn) && FVector::DistSquared2D(Pawn->GetActorLocation(), It->GetPanelLocation()) < Mine)
                bNear = false;
    }
    if (Prompt) Prompt->SetHiddenInGame(!bNear);
    const bool bCamera = Player && Player->PlayerCameraManager;
    const FVector Camera = bCamera ? Player->PlayerCameraManager->GetCameraLocation() : FVector::ZeroVector;
    if (bNear)
    {
        Prompt->SetText(FText::FromString(FString::Printf(TEXT("[E] %s %s"), bActive ? TEXT("APAGAR") : TEXT("ENCENDER"), *BeltName)));
        if (bCamera)  // TextRender reads along +X: turn it toward the camera.
            Prompt->SetWorldRotation((Camera - Prompt->GetComponentLocation()).Rotation());
    }
    // The sign pops up (with a small overshoot) when the belt fills and turns upright toward the camera.
    SignShown = FMath::FInterpConstantTo(SignShown, bFull ? 1.0f : 0.0f, DeltaSeconds, 1.0f / 0.35f);
    const bool bSign = SignShown > 0.01f && Sign->GetStaticMesh();
    Sign->SetHiddenInGame(!bSign);
    SignText->SetHiddenInGame(!bSign);
    if (bSign)
    {
        const float Pop = FMath::InterpEaseOut(0.0f, 1.0f, SignShown, 2.5f) + 0.15f * FMath::Sin(SignShown * PI);
        Sign->SetRelativeScale3D(FVector(FMath::Max(Pop, KINDA_SMALL_NUMBER)));
        if (bCamera)
            Sign->SetWorldRotation(FRotator(0, (Camera - Sign->GetComponentLocation()).Rotation().Yaw, 0));
    }
    if (!bFull) bDetailOpen = false;
    // "[E] AGARRAR CAJA" over the box in reach, when the hands are free and it is nearer than the panel.
    double BoxDistance = 0.0;
    const int32 Reachable = Pawn ? NearestBox(Pawn, BoxDistance) : INDEX_NONE;
    const auto* Carry = Pawn ? Pawn->FindComponentByClass<UFactoryCarryComponent>() : nullptr;
    const bool bBoxPrompt = Reachable != INDEX_NONE && Carry && !Carry->IsCarrying()
        && (!Button || BoxDistance < FVector::DistSquared2D(Pawn->GetActorLocation(), GetPanelLocation()));
    BoxPrompt->SetHiddenInGame(!bBoxPrompt);
    if (bBoxPrompt)
    {
        BoxPrompt->SetWorldLocation(Boxes[Reachable]->GetComponentLocation() + FVector(0, 0, 70));
        if (bCamera) BoxPrompt->SetWorldRotation((Camera - BoxPrompt->GetComponentLocation()).Rotation());
    }
    const float Length = FVector::Dist(Start, End);
    if (BoxMesh && bActive)
    {
        // A new box comes out at a random spot across the entrance where it fits.
        SinceLastBox += DeltaSeconds;
        float FreeSide = 0.0f;
        const bool bRoom = FindFreeSide(FreeSide);
        if (SinceLastBox >= SecondsBetweenBoxes && bRoom)
            SpawnBox(FreeSide);

        // Boxes ride forward until the far end or a box ahead that overlaps them across (furthest first).
        TArray<int32> Order;
        for (int32 Index = 0; Index < Boxes.Num(); ++Index) Order.Add(Index);
        Order.Sort([this](int32 A, int32 B) { return Travelled[A] > Travelled[B]; });
        bool bAllParked = !bRoom;
        for (int32 Rank = 0; Rank < Order.Num(); ++Rank)
        {
            const int32 Index = Order[Rank];
            float Limit = Length;
            int32 Blocker = INDEX_NONE;
            for (int32 Ahead = 0; Ahead < Rank; ++Ahead)
                if (FMath::Abs(Lateral[Order[Ahead]] - Lateral[Index]) < SameLane()
                    && Travelled[Order[Ahead]] - BoxSpacing - ExtraGap[Index] < Limit)
                {
                    Limit = FMath::Max(Travelled[Order[Ahead]] - BoxSpacing - ExtraGap[Index], 0.0f);
                    Blocker = Order[Ahead];
                }
            Travelled[Index] = FMath::Max(Travelled[Index], FMath::Min(Travelled[Index] + Speed * DeltaSeconds, Limit));
            const bool bStopped = Travelled[Index] >= Limit - 0.5f;
            if (bStopped && Motion[Index].bMoving)
            {
                // It just ran into something: it tips forward and turns a little; what it hit rocks too.
                Bump(Index, Blocker == INDEX_NONE ? 1.3f : 1.0f);
                if (Blocker != INDEX_NONE) Bump(Blocker, 0.45f);
            }
            Motion[Index].bMoving = !bStopped;
            bAllParked &= bStopped;
        }
        if (bAllParked)
        {
            SetBeltOn(false);
            bFull = true;
            bStoppedWhenFull = true;
        }
    }
    PlaceBoxes(DeltaSeconds);
}

void AFactoryDispatchBelt::Bump(int32 Index, float Strength)
{
    FDispatchBoxMotion& Rock = Motion[Index];
    const float Hit = Strength * BumpStrength;
    Rock.TiltSpeed += 55.0f * Hit;
    Rock.YawSpeed += FMath::FRandRange(-30.0f, 30.0f) * Hit;
    Rock.NudgeSpeed += FMath::FRandRange(-12.0f, 12.0f) * Hit;
    // Settles a little differently each time, as a real box would.
    Rock.RestYaw = FMath::Clamp(Rock.RestYaw + FMath::FRandRange(-2.5f, 2.5f) * Hit, -2.0f * MaxYawJitter - 2.0f, 2.0f * MaxYawJitter + 2.0f);
}

void AFactoryDispatchBelt::PlaceBoxes(float DeltaSeconds)
{
    const float Length = FVector::Dist(Start, End);
    const FVector Side = FVector::CrossProduct(End - Start, FVector::UpVector).GetSafeNormal();
    const float Time = GetWorld()->GetTimeSeconds();
    // Damped springs, in small steps so they stay stable at any frame rate.
    constexpr float Stiffness = 150.0f, Damping = 10.0f, MaxStep = 1.0f / 90.0f;
    const int32 Steps = FMath::Clamp(FMath::CeilToInt(DeltaSeconds / MaxStep), 1, 8);
    const float Step = DeltaSeconds / Steps;
    for (int32 Index = 0; Index < Boxes.Num(); ++Index)
    {
        if (!Boxes[Index]) continue;
        FDispatchBoxMotion& Rock = Motion[Index];
        for (int32 Sub = 0; Sub < Steps; ++Sub)
        {
            Rock.TiltSpeed += (-Stiffness * Rock.Tilt - Damping * Rock.TiltSpeed) * Step;
            Rock.YawSpeed += (-Stiffness * (Rock.Yaw - Rock.RestYaw) - Damping * Rock.YawSpeed) * Step;
            Rock.NudgeSpeed += (-Stiffness * Rock.Nudge - Damping * Rock.NudgeSpeed) * Step;
            Rock.Tilt = FMath::Clamp(Rock.Tilt + Rock.TiltSpeed * Step, -8.0f, 8.0f);
            Rock.Yaw += Rock.YawSpeed * Step;
            Rock.Nudge = FMath::Clamp(Rock.Nudge + Rock.NudgeSpeed * Step, -3.0f, 3.0f);
        }
        // Riding on the rollers it shivers slightly; tipped, its low edge stays on the belt.
        const float Shiver = Rock.bMoving && bActive ? 0.25f * FMath::Sin(Time * 38.0f + Rock.Phase) : 0.0f;
        const float Lift = 20.0f * FMath::Sin(FMath::DegreesToRadians(FMath::Abs(Rock.Tilt)));
        const float Alpha = Length > KINDA_SMALL_NUMBER ? Travelled[Index] / Length : 1.0f;
        const FVector Location = FMath::Lerp(Start, End, Alpha) + Side * (Lateral[Index] + Rock.Nudge) + FVector::UpVector * (Lift + Shiver);
        const FQuat Tip(Side, -FMath::DegreesToRadians(Rock.Tilt));   // + tilt leans the top toward End
        const FQuat Turn(FVector::UpVector, FMath::DegreesToRadians(Rock.Yaw));
        Boxes[Index]->SetRelativeLocationAndRotation(Location, Tip * Turn);
    }
}

AFactoryBeltButton::AFactoryBeltButton()
{
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Panel = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Panel"));
    Panel->SetupAttachment(RootComponent);
    Panel->SetCollisionProfileName(TEXT("BlockAll"));
    Prompt = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Prompt"));
    Prompt->SetupAttachment(RootComponent);
    Prompt->SetRelativeLocation(FVector(0, 0, 150));
    Prompt->SetHorizontalAlignment(EHTA_Center);
    Prompt->SetVerticalAlignment(EVRTA_TextCenter);
    Prompt->SetWorldSize(18.0f);
    Prompt->SetTextRenderColor(FColor(46, 232, 199));
    Prompt->SetText(FText::GetEmpty());  // the belt fills it in play; empty, nothing shows in the editor
    Prompt->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Prompt->SetHiddenInGame(true);
}
