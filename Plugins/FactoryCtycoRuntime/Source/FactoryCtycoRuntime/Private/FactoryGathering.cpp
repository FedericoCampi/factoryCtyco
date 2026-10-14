#include "FactoryGathering.h"
#include "FactoryDemo.h"
#include "FactoryElevator.h"
#include "FactoryMachineSwitch.h"
#include "FactoryMeltProcess.h"
#include "FactoryDispatchBelt.h"
#include "FactoryGateBarrier.h"
#include "FactoryLoadingBelt.h"
#include "FactoryRollDoor.h"
#include "FactoryCarry.h"
#include "FactoryHover.h"
#include "Components/InputComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "UObject/ConstructorHelpers.h"

float UFactoryResourceDefinition::GetCargoSize() const
{
    // A piece of another material: a percentage of that one's size (a few links at most; a loop stops there).
    const UFactoryResourceDefinition* Item = this;
    float Factor = 1.0f;
    for (int32 Depth = 0; Item->SizeFrom && Item->SizeFrom != Item && Depth < 8; ++Depth)
    {
        Factor *= Item->SizePercent / 100.0f;
        Item = Item->SizeFrom;
    }
    return Item->CargoSize * Factor;
}

FVector UFactoryResourceDefinition::CargoScale() const
{
    const float Longest = PickupMesh ? PickupMesh->GetBoundingBox().GetSize().GetMax() : 1.0f;
    return FVector(GetCargoSize() / FMath::Max(Longest, 1.0f));
}

int32 UFactoryInventoryComponent::GetTotal() const
{
    int32 Total = 0;
    for (const auto& Item : Items) Total += Item.Value;
    return Total;
}
int32 UFactoryInventoryComponent::GetFreeSpace() const { return FMath::Max(0, Capacity - GetTotal()); }
int32 UFactoryInventoryComponent::GetQuantity(FName ItemId) const { return Items.FindRef(ItemId); }
int32 UFactoryInventoryComponent::AddItem(UFactoryResourceDefinition* Resource, int32 Quantity)
{
    if (!Resource || Resource->ItemId.IsNone() || Quantity <= 0) return 0;
    const int32 Accepted = FMath::Min(Quantity, GetFreeSpace());
    if (Accepted > 0)
    {
        Items.FindOrAdd(Resource->ItemId) += Accepted;
        Definitions.Add(Resource->ItemId, Resource);
    }
    return Accepted;
}
int32 UFactoryInventoryComponent::RemoveItem(FName ItemId, int32 Quantity)
{
    if (Quantity <= 0) return 0;
    int32* Existing = Items.Find(ItemId);
    if (!Existing) return 0;
    const int32 Removed = FMath::Min(*Existing, Quantity);
    *Existing -= Removed;
    if (*Existing == 0) Items.Remove(ItemId);
    return Removed;
}

AFactoryResourcePile::AFactoryResourcePile()
{
    PrimaryActorTick.bCanEverTick = false;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    MetalPieces = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("MetalPieces"));
    AccentPieces = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("AccentPieces"));
    CustomVisual = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("CustomVisual"));
    FocusMarker = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FocusMarker"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    for (UStaticMeshComponent* Component : {static_cast<UStaticMeshComponent*>(MetalPieces), static_cast<UStaticMeshComponent*>(AccentPieces), CustomVisual.Get(), FocusMarker.Get()})
    {
        Component->SetupAttachment(RootComponent);
        Component->SetCollisionProfileName(TEXT("NoCollision"));
    }
    MetalPieces->SetStaticMesh(Cube.Object);
    AccentPieces->SetStaticMesh(Cube.Object);
    FocusMarker->SetStaticMesh(Cylinder.Object);
    FocusMarker->SetRelativeLocation(FVector(0, 0, 0));
    FocusMarker->SetRelativeScale3D(FVector(0.95f, 0.95f, 0.004f));
    FocusMarker->SetCastShadow(false);
    FocusMarker->SetVisibility(false);
}
void AFactoryResourcePile::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    RefreshVisuals();
}
void AFactoryResourcePile::RefreshVisuals()
{
    MetalPieces->ClearInstances();
    AccentPieces->ClearInstances();
    if (MetalMaterial) MetalPieces->SetMaterial(0, MetalMaterial);
    if (AccentMaterial) AccentPieces->SetMaterial(0, AccentMaterial);
    if (FocusMaterial) FocusMarker->SetMaterial(0, FocusMaterial);
    const bool bCustom = Resource && Resource->PickupMesh;
    CustomVisual->SetVisibility(bCustom);
    MetalPieces->SetVisibility(!bCustom);
    AccentPieces->SetVisibility(!bCustom);
    if (bCustom)
    {
        CustomVisual->SetStaticMesh(Resource->PickupMesh);
        CustomVisual->SetRelativeScale3D(Resource->PickupScale);
    }
    else
    {
        for (int32 Index = 0; Index < 9; ++Index)
        {
            const float X = (Index % 3 - 1) * 22.0f;
            const float Y = (Index / 3 - 1) * 19.0f;
            const FVector Location(X, Y, 5.0f + (Index % 3) * 4.0f);
            const FRotator Rotation((Index % 2) * 9.0f, Index * 47.0f, (Index % 3 - 1) * 8.0f);
            const FVector Scale(0.42f, 0.12f + (Index % 2) * 0.09f, 0.075f);
            UInstancedStaticMeshComponent* Pieces = Index % 3 == 0 ? AccentPieces.Get() : MetalPieces.Get();
            Pieces->AddInstance(FTransform(Rotation, Location, Scale));
        }
    }
    SetActorHiddenInGame(Amount <= 0);
}
void AFactoryResourcePile::SetFocused(bool bFocused) { FocusMarker->SetVisibility(bFocused && Amount > 0); }
int32 AFactoryResourcePile::TransferTo(UFactoryInventoryComponent* Inventory)
{
    if (!Inventory || Amount <= 0 || !Resource) return 0;
    const int32 Accepted = Inventory->AddItem(Resource, Amount);
    Amount -= Accepted;
    if (Amount == 0)
    {
        SetFocused(false);
        SetActorHiddenInGame(true);
    }
    return Accepted;
}

UFactoryGatheringComponent::UFactoryGatheringComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickInterval = 0.1f;
}
void UFactoryGatheringComponent::BeginPlay()
{
    Super::BeginPlay();
    // Pawn-owned input components are gathered automatically by PlayerController.
    GatheringInput = NewObject<UInputComponent>(GetOwner(), TEXT("FactoryGatheringInput"));
    GatheringInput->RegisterComponent();
    GatheringInput->bBlockInput = false;
    GatheringInput->BindKey(EKeys::E, IE_Pressed, this, &UFactoryGatheringComponent::Interact);
    GatheringInput->BindKey(EKeys::I, IE_Pressed, this, &UFactoryGatheringComponent::ToggleInventory);
    GatheringInput->BindKey(EKeys::M, IE_Pressed, this, &UFactoryGatheringComponent::ToggleMusic);
    GatheringInput->BindKey(EKeys::N, IE_Pressed, this, &UFactoryGatheringComponent::ToggleSounds);
    // Carrying boxes from the dispatch belts.
    if (!GetOwner()->FindComponentByClass<UFactoryCarryComponent>())
    {
        auto* Carry = NewObject<UFactoryCarryComponent>(GetOwner(), TEXT("FactoryCarry"));
        Carry->RegisterComponent();
    }
    // Outline on whatever the mouse can click.
    if (!GetOwner()->FindComponentByClass<UFactoryHoverComponent>())
        NewObject<UFactoryHoverComponent>(GetOwner(), TEXT("FactoryHover"))->RegisterComponent();
}
bool UFactoryGatheringComponent::CanReach(const AFactoryResourcePile* Pile) const
{
    if (!IsValid(Pile) || Pile->Amount <= 0 || !Pile->Resource) return false;
    const FVector Origin = GetOwner()->GetActorLocation();
    const FVector Target = Pile->GetActorLocation();
    if (FVector::DistSquared2D(Origin, Target) > FMath::Square(InteractionDistance) || FMath::Abs(Origin.Z - Target.Z) > 150.0f) return false;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(ResourceReach), false, GetOwner());
    const bool bBlocked = GetWorld()->LineTraceSingleByChannel(Hit, Origin + FVector(0, 0, 30), Target + FVector(0, 0, 35), ECC_Visibility, Params);
    return !bBlocked || Hit.GetActor() == Pile;
}
void UFactoryGatheringComponent::RefreshTarget()
{
    AFactoryResourcePile* Closest = nullptr;
    double BestDistance = TNumericLimits<double>::Max();
    const APawn* Pawn = Cast<APawn>(GetOwner());
    if (Pawn && Pawn->IsLocallyControlled())
    {
        for (TActorIterator<AFactoryResourcePile> It(GetWorld()); It; ++It)
        {
            const double Distance = FVector::DistSquared2D(GetOwner()->GetActorLocation(), It->GetActorLocation());
            if (Distance < BestDistance && CanReach(*It)) { Closest = *It; BestDistance = Distance; }
        }
    }
    if (FocusedPile != Closest)
    {
        if (IsValid(FocusedPile)) FocusedPile->SetFocused(false);
        FocusedPile = Closest;
        if (FocusedPile) FocusedPile->SetFocused(true);
    }
}
void UFactoryGatheringComponent::Interact()
{
    for (TActorIterator<AFactoryElevator> It(GetWorld()); It; ++It)
        if (It->TryInteract(GetOwner())) return;
    // With a box in the hands, E sets it down.
    UFactoryCarryComponent* Carry = GetOwner()->FindComponentByClass<UFactoryCarryComponent>();
    // Inside a barrier's booth E works the barrier, box in hand or not.
    for (TActorIterator<AFactoryGateBarrier> It(GetWorld()); It; ++It)
        if (It->TryInteract(GetOwner())) return;
    // At a roll-up door's wall button E opens or shuts it.
    for (TActorIterator<AFactoryRollDoor> It(GetWorld()); It; ++It)
        if (It->TryInteract(GetOwner())) return;
    // With a box in hand at a truck loading belt, E puts it on the belt (or waits if the truck cannot take it).
    if (Carry && Carry->IsCarrying())
    {
        AFactoryLoadingBelt* NearestLoading = nullptr;
        float NearestLoadingDistance = TNumericLimits<float>::Max();
        for (TActorIterator<AFactoryLoadingBelt> It(GetWorld()); It; ++It)
        {
            float Along = 0.0f;
            const float Gap = It->DistanceTo(GetOwner(), Along);
            if (Gap <= It->InteractionRadius && Gap < NearestLoadingDistance) { NearestLoadingDistance = Gap; NearestLoading = *It; }
        }
        if (NearestLoading && NearestLoading->TryLoad(GetOwner())) return;
    }
    if (Carry && Carry->IsCarrying())
    {
        Carry->Drop();
        return;
    }
    for (TActorIterator<AFactoryMachineSwitch> It(GetWorld()); It; ++It)
        if (It->TryInteract(GetOwner())) return;
    // At the furnace: light it or open the pour; at its container: take the ingot.
    for (TActorIterator<AFactoryMeltProcess> It(GetWorld()); It; ++It)
        if (It->TryInteract(GetOwner())) return;
    // Belt panels can stand close together: E goes to the nearest one in reach.
    AFactoryDispatchBelt* NearestBelt = nullptr;
    double NearestBeltDistance = TNumericLimits<double>::Max();
    // A box on a belt is taken when it is nearer than any panel.
    AFactoryDispatchBelt* BoxBelt = nullptr;
    int32 BoxIndex = INDEX_NONE;
    double BoxDistance = TNumericLimits<double>::Max();
    for (TActorIterator<AFactoryDispatchBelt> It(GetWorld()); It; ++It)
    {
        double Distance = 0.0;
        const int32 Index = Carry ? It->NearestBox(GetOwner(), Distance) : INDEX_NONE;
        if (Index != INDEX_NONE && Distance < BoxDistance) { BoxDistance = Distance; BoxIndex = Index; BoxBelt = *It; }
        if (!It->InReach(GetOwner())) continue;
        Distance = FVector::DistSquared2D(GetOwner()->GetActorLocation(), It->GetPanelLocation());
        if (Distance < NearestBeltDistance) { NearestBeltDistance = Distance; NearestBelt = *It; }
    }
    if (BoxBelt && BoxDistance < NearestBeltDistance)
    {
        Carry->Take(BoxBelt->TakeBox(BoxIndex));
        return;
    }
    if (NearestBelt && NearestBelt->TryInteract(GetOwner())) return;
    if (Carry && Carry->PickLoose()) return;
    if (auto* Demo = GetOwner()->FindComponentByClass<UFactoryDemoComponent>())
        if (Demo->InteractMachine()) return;
    RefreshTarget(); // Validate range and line of sight again at the moment of collection.
    UFactoryInventoryComponent* Inventory = GetOwner()->FindComponentByClass<UFactoryInventoryComponent>();
    if (!FocusedPile || !Inventory) return;
    const FString Name = FocusedPile->Resource->DisplayName.ToString();
    const int32 Accepted = FocusedPile->TransferTo(Inventory);
    Notification = Accepted > 0 ? FString::Printf(TEXT("+%d %s"), Accepted, *Name) : TEXT("Inventario lleno");
    NotificationUntil = GetWorld()->GetTimeSeconds() + 2.5f;
    RefreshTarget();
}
void UFactoryGatheringComponent::ToggleInventory() { bInventoryOpen = !bInventoryOpen; }
void UFactoryGatheringComponent::ToggleMusic()
{
    // M: the music (silencing everything sits on the info panel, key I).
    if (const APawn* Pawn = Cast<APawn>(GetOwner()))
        if (const APlayerController* Player = Cast<APlayerController>(Pawn->GetController()))
            if (auto* HUD = Cast<AFactoryDemoHUD>(Player->GetHUD())) HUD->ToggleMusic();
}
void UFactoryGatheringComponent::ToggleSounds()
{
    // N: every other sound.
    if (const APawn* Pawn = Cast<APawn>(GetOwner()))
        if (const APlayerController* Player = Cast<APlayerController>(Pawn->GetController()))
            if (auto* HUD = Cast<AFactoryDemoHUD>(Player->GetHUD())) HUD->ToggleSounds();
}
void UFactoryGatheringComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    RefreshTarget();
}
void UFactoryGatheringComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if (IsValid(FocusedPile)) FocusedPile->SetFocused(false);
    if (GatheringInput) GatheringInput->DestroyComponent();
    Super::EndPlay(Reason);
}

void AFactoryGatheringHUD::DrawHUD()
{
    Super::DrawHUD();
    APawn* Pawn = PlayerOwner ? PlayerOwner->GetPawn() : nullptr;
    if (!Canvas || !Pawn) return;
    UFactoryInventoryComponent* Inventory = Pawn->FindComponentByClass<UFactoryInventoryComponent>();
    UFactoryGatheringComponent* Gathering = Pawn->FindComponentByClass<UFactoryGatheringComponent>();
    if (!Inventory || !Gathering) return;
    const float S = FMath::Clamp(FMath::Min(Canvas->SizeX / 1440.0f, Canvas->SizeY / 900.0f), 0.65f, 1.6f);
    const float W = Canvas->SizeX / S, H = Canvas->SizeY / S;
    const FLinearColor Panel(0.025f, 0.035f, 0.05f, 0.96f), Edge(0.18f, 0.24f, 0.29f, 1);
    const FLinearColor White(0.93f, 0.95f, 0.97f, 1), Muted(0.60f, 0.68f, 0.73f, 1);
    const FLinearColor Amber(1.0f, 0.56f, 0.18f, 1), Cyan(0.25f, 0.89f, 0.88f, 1);
    auto Rect = [&](FLinearColor Color, float X, float Y, float Width, float Height) { DrawRect(Color, X*S, Y*S, Width*S, Height*S); };
    auto Text = [&](const FString& Value, float X, float Y, float Scale, FLinearColor Color) { DrawText(Value, Color, X*S, Y*S, GEngine->GetMediumFont(), Scale*S); };
    auto Box = [&](float X, float Y, float Width, float Height) { Rect(Edge, X, Y, Width, Height); Rect(Panel, X+1, Y+1, Width-2, Height-2); };
    const int32 Scrap = Inventory->GetQuantity(TEXT("Scrap"));
    Box(24, 24, 304, 126);
    Rect(Amber, 24, 24, 4, 126);
    Text(TEXT("PATIO DE RECICLAJE"), 44, 39, 0.95f, Amber);
    Text(FString::Printf(TEXT("%d"), Scrap), 44, 67, 2.1f, White);
    Text(TEXT("CHATARRA"), 115, 82, 0.95f, Muted);
    Text(FString::Printf(TEXT("Carga %d / %d"), Inventory->GetTotal(), Inventory->Capacity), 44, 124, 0.85f, Muted);
    Text(TEXT("[ I ] INVENTARIO"), 195, 124, 0.78f, White);

    Box(W-368, 24, 344, 105);
    Text(Scrap >= 30 ? TEXT("OBJETIVO CUMPLIDO") : TEXT("PRIMEROS RECURSOS"), W-348, 39, 0.95f, Scrap >= 30 ? Cyan : Amber);
    Text(Scrap >= 30 ? TEXT("Reserva de chatarra conseguida") : TEXT("Recolectá 30 de chatarra"), W-348, 67, 1.0f, White);
    Rect(Edge, W-348, 103, 304, 5);
    Rect(Cyan, W-348, 103, 304*FMath::Clamp(Scrap/30.0f, 0.0f, 1.0f), 5);

    if (Gathering->bInventoryOpen)
    {
        Box(24, 166, 344, 340);
        Text(TEXT("INVENTARIO"), 44, 186, 1.25f, White);
        Text(TEXT("[ I ] Cerrar"), 266, 190, 0.85f, Muted);
        Rect(Edge, 44, 224, 304, 1);
        float Y = 244;
        TArray<FName> Keys;
        Inventory->Items.GetKeys(Keys);
        Keys.Sort(FNameLexicalLess());
        if (Keys.IsEmpty()) Text(TEXT("Todavía no tenés recursos."), 44, Y, 0.95f, Muted);
        for (FName Id : Keys)
        {
            const UFactoryResourceDefinition* Definition = Inventory->Definitions.FindRef(Id);
            Rect(FLinearColor(0.07f, 0.10f, 0.12f, 1), 44, Y, 304, 66);
            Rect(Definition ? Definition->Color : Amber, 56, Y+15, 30, 30);
            Text(Definition ? Definition->DisplayName.ToString() : Id.ToString(), 100, Y+10, 1.1f, White);
            Text(FString::Printf(TEXT("%d unidades"), Inventory->GetQuantity(Id)), 100, Y+35, 0.88f, Muted);
            Y += 78;
        }
        Text(FString::Printf(TEXT("CAPACIDAD  %d / %d"), Inventory->GetTotal(), Inventory->Capacity), 44, 450, 0.95f, White);
        Rect(Edge, 44, 478, 304, 6);
        Rect(Amber, 44, 478, 304*FMath::Clamp(Inventory->GetTotal()/static_cast<float>(FMath::Max(1, Inventory->Capacity)), 0.0f, 1.0f), 6);
    }
    if (Gathering->FocusedPile)
    {
        const bool bFull = Inventory->GetFreeSpace() == 0;
        Box(W/2-208, H-162, 416, 74);
        Text(bFull ? TEXT("INVENTARIO LLENO") : TEXT("[ E ]  RECOGER CHATARRA"), W/2-188, H-149, 1.1f, bFull ? Amber : Cyan);
        Text(FString::Printf(TEXT("Montón: %d unidades  |  Espacio libre: %d"), Gathering->FocusedPile->Amount, Inventory->GetFreeSpace()), W/2-188, H-119, 0.85f, Muted);
    }
    if (Gathering->NotificationUntil > GetWorld()->GetTimeSeconds())
    {
        Text(Gathering->Notification, W/2-80, H-207, 1.4f, Cyan);
    }
    Rect(Panel, 0, H-62, W, 62);
    Text(TEXT("WASD  Mover     SHIFT  Rápido     E  Recoger     I  Inventario"), 24, H-50, 0.95f, White);
    Text(TEXT("Rueda  Zoom     Botón central  Desplazar cámara     Inicio  Centrar"), 24, H-25, 0.8f, Muted);
}
