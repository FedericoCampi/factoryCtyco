#include "FactoryDemo.h"
#include "FactoryDispatchBelt.h"
#include "FactoryElevator.h"
#include "FactoryMission.h"
#include "FactoryStaff.h"
#include "FactoryCameraComponent.h"
#include "EngineUtils.h"
#include "Engine/Canvas.h"
#include "AudioDevice.h"
#include "Engine/Texture2D.h"
#include "Engine/Engine.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"

bool AFactoryDemoHUD::ClickCatalog(float X, float Y)
{
    APawn* Pawn = PlayerOwner ? PlayerOwner->GetPawn() : nullptr;
    auto* Demo = Pawn ? Pawn->FindComponentByClass<UFactoryDemoComponent>() : nullptr;
    if (!Demo || !Demo->bBuilding || !Demo->Factory) return false;
    for (int32 Index = 0; Index < CatalogButtons.Num(); ++Index)
        if (Demo->Factory->Catalog.IsValidIndex(Index) && Demo->Factory->Catalog[Index] && CatalogButtons[Index].IsInside(FVector2D(X, Y))) { Demo->SelectBuilding(Index); return true; }
    return false;
}

bool AFactoryDemoHUD::ClickElevator(float X, float Y)
{
    AFactoryElevator* Elevator = AFactoryElevator::FindOpenMenu(GetWorld());
    if (!Elevator) return false;
    for (const TPair<FBox2D, int32>& Row : ElevatorButtons)
        if (Row.Key.IsInside(FVector2D(X, Y))) { Elevator->SelectFloor(Row.Value); return true; }
    return false;
}

void AFactoryDemoHUD::DrawElevatorMenu(float S, float W, float H)
{
    ElevatorButtons.Reset();
    AFactoryElevator* Elevator = AFactoryElevator::FindOpenMenu(GetWorld());
    if (!Elevator) return;
    const FLinearColor Panel(.012f,.023f,.032f,.95f), Border(.055f,.10f,.12f,1), White(.93f,.96f,.97f,1);
    const FLinearColor Muted(.60f,.70f,.74f,1), Cyan(.18f,.91f,.78f,1), Amber(1,.63f,.22f,1), Row(.03f,.06f,.075f,1);
    auto Rect = [&](FLinearColor Color, float X, float Y, float Width, float Height) { DrawRect(Color, X*S, Y*S, Width*S, Height*S); };
    auto Text = [&](const FString& Value, float X, float Y, float Scale, FLinearColor Color) { DrawText(Value, Color, X*S, Y*S, GEngine->GetMediumFont(), Scale*S); };
    auto RightText = [&](const FString& Value, float Right, float Y, float Scale, FLinearColor Color) { float TextWidth = 0, TextHeight = 0; GetTextSize(Value,TextWidth,TextHeight,GEngine->GetMediumFont(),Scale*S); Text(Value,Right-TextWidth/S,Y,Scale,Color); };
    const TArray<AFactoryElevator*> Floors = Elevator->GetFloors();
    const int32 Here = Floors.IndexOfByKey(Elevator);
    // The floor the guide asks for pulses in orange with an arrow.
    const FString Wanted = GuideElevatorStop();
    const float Pulse = .5f + .5f * FMath::Sin(GetWorld()->GetRealTimeSeconds() * 6.0f);
    const float RowH = 54, Width = 380, Height = 92 + RowH * Floors.Num() + 34;
    const float X = W - Width - 24, Y = FMath::Max(24.0f, (H - Height) / 2);
    Rect(FLinearColor(0,0,0,.18f),X+3,Y+4,Width,Height);
    Rect(Border,X,Y,Width,Height);
    Rect(Panel,X+1,Y+1,Width-2,Height-2);
    Rect(Cyan,X,Y,Width,3);
    Text(TEXT("ASCENSOR"),X+20,Y+18,1.1f,Cyan);
    Text(FString::Printf(TEXT("Estás en el piso %d · %s"), Here + 1, *Elevator->StopName),X+20,Y+50,.8f,Muted);
    // Highest floor on top, like the buttons of a real elevator.
    float RowY = Y + 82;
    for (int32 Index = Floors.Num() - 1; Index >= 0; --Index, RowY += RowH)
    {
        const AFactoryElevator* Floor = Floors[Index];
        const bool bHere = Index == Here;
        const bool bWanted = !bHere && !Wanted.IsEmpty() && Floor->StopName.Equals(Wanted, ESearchCase::IgnoreCase);
        Rect(bHere ? FLinearColor(.04f,.09f,.10f,1) : bWanted ? FMath::Lerp(Row, FLinearColor(.35f,.16f,.02f,1), Pulse) : Row,X+14,RowY,Width-28,RowH-8);
        Rect(bHere ? Muted : bWanted ? Amber : Cyan,X+14,RowY,bWanted ? 8 : 4,RowH-8);
        if (bWanted) Text(TEXT("▶"),X-(30+6*Pulse),RowY+10,1.1f,Amber);
        Text(FString::Printf(TEXT("%d"), Index + 1),X+30,RowY+10,1.15f,bHere ? Muted : White);
        Text(Floor->StopName,X+66,RowY+13,.95f,bHere ? Muted : White);
        const FString Action = bHere ? TEXT("ESTÁS ACÁ") : Index > Here ? TEXT("▲ SUBIR") : TEXT("▼ BAJAR");
        RightText(Action,X+Width-28,RowY+14,.85f,bHere ? Muted : Index > Here ? Cyan : Amber);
        if (!bHere) ElevatorButtons.Add(TPair<FBox2D, int32>(FBox2D(FVector2D(X+14, RowY)*S, FVector2D(X+Width-14, RowY+RowH-8)*S), Index + 1));
    }
    Text(TEXT("Clic o número: ir al piso   ·   E: cerrar"),X+20,RowY+6,.72f,Muted);
}

bool AFactoryDemoHUD::ClickMoneyBar(float X, float Y)
{
    if (!MuteCorner.bIsValid || !MuteCorner.IsInside(FVector2D(X, Y))) return false;
    ToggleMute();
    return true;
}

bool AFactoryDemoHUD::ClickInfoPanel(float X, float Y)
{
    const FVector2D At(X, Y);
    for (int32 Tab = 0; Tab < 2; ++Tab)
        if (TabButtons[Tab].bIsValid && TabButtons[Tab].IsInside(At)) { SetInfoTab(Tab); return true; }
    if (HireButton.bIsValid && HireButton.IsInside(At))
    {
        if (auto* Staff = UFactoryStaffSubsystem::Get(this)) Staff->Hire(TEXT("Barrera"));
        return true;
    }
    if (!MuteButton.bIsValid || !MuteButton.IsInside(At)) return false;
    ToggleMute();
    return true;
}

void AFactoryDemoHUD::ToggleMute()
{
    bMuted = !bMuted;
    MutedAt = GetWorld()->GetRealTimeSeconds();
    if (FAudioDeviceHandle Device = GetWorld()->GetAudioDevice()) Device->SetTransientPrimaryVolume(bMuted ? 0.0f : 1.0f);
}

void AFactoryDemoHUD::DrawHUD()
{
    Super::DrawHUD();
    APawn* Pawn = PlayerOwner ? PlayerOwner->GetPawn() : nullptr;
    auto* Demo = Pawn ? Pawn->FindComponentByClass<UFactoryDemoComponent>() : nullptr;
    if (!Canvas || !Demo || !Demo->Factory || !Demo->Inventory()) return;
    auto* Factory = Demo->Factory.Get();
    auto* Inventory = Demo->Inventory();
    auto* Gathering = Pawn->FindComponentByClass<UFactoryGatheringComponent>();
    const float S = FMath::Clamp(FMath::Min(Canvas->SizeX / 1440.0f, Canvas->SizeY / 900.0f), .5f, 1.8f);
    const float W = Canvas->SizeX / S, H = Canvas->SizeY / S;
    const FLinearColor Panel(.012f,.023f,.032f,.94f), Border(.055f,.10f,.12f,1), White(.93f,.96f,.97f,1);
    const FLinearColor Muted(.60f,.70f,.74f,1), Cyan(.18f,.91f,.78f,1), Amber(1,.63f,.22f,1), Red(1,.30f,.26f,1);
    const FLinearColor Recess(.022f,.042f,.052f,.96f);
    auto Rect = [&](FLinearColor Color, float X, float Y, float Width, float Height) { DrawRect(Color, X*S, Y*S, Width*S, Height*S); };
    auto Text = [&](const FString& Value, float X, float Y, float Scale, FLinearColor Color) { DrawText(Value, Color, X*S, Y*S, GEngine->GetMediumFont(), Scale*S); };
    auto Box = [&](float X, float Y, float Width, float Height) { Rect(FLinearColor(0,0,0,.18f),X+3,Y+4,Width,Height); Rect(Border,X,Y,Width,Height); Rect(Panel,X+1,Y+1,Width-2,Height-2); };
    auto Bar = [&](float X, float Y, float Width, float Height, float Fraction, FLinearColor Color) { Rect(Recess,X,Y,Width,Height); Rect(Color,X,Y,Width*FMath::Clamp(Fraction,0.0f,1.0f),Height); };
    auto RightText = [&](const FString& Value, float Right, float Y, float Scale, FLinearColor Color) { float TextWidth = 0, TextHeight = 0; GetTextSize(Value,TextWidth,TextHeight,GEngine->GetMediumFont(),Scale*S); Text(Value,Right-TextWidth/S,Y,Scale,Color); };
    auto FitText = [&](const FString& Value, float X, float Y, float Width, float Scale, FLinearColor Color) { float TextWidth=0,TextHeight=0; GetTextSize(Value,TextWidth,TextHeight,GEngine->GetMediumFont(),Scale*S); Text(Value,X,Y,TextWidth>Width*S ? Scale*Width*S/FMath::Max(TextWidth,1.0f) : Scale,Color); };
    auto Name = [&](FName Id) { auto* Item = Factory->Resource(Id); return Item ? Item->DisplayName.ToString() : Id.ToString(); };
    // The start-of-game story covers everything until it is passed.
    if (DrawGuideCover(S, W, H)) return;
    DrawBeltDetail(S, W);
    DrawElevatorMenu(S, W, H);
    // The recycling demo (scrap, plates, objective) is retired: its panels and hints stay hidden.
    if (!bShowRecyclingHUD)
    {
        Rect(Panel,0,H-44,W,44);
        Rect(Border,0,H-44,W,1);
        Text(TEXT("WASD Mover   SHIFT Rápido   E Usar   I Info   M Silenciar   Clic Personaje: seguir   Flechas/Central Mover cámara   Rueda Zoom   Arrastrar Der. Orbitar   Inicio Seguirme"),24,H-31,.86f,White);
        // Camera state, right of the hints: free or following someone.
        if (const auto* Camera = Pawn->FindComponentByClass<UFactoryCameraComponent>(); Camera && Camera->bStartFree)
        {
            const AActor* Target = Camera->GetFollowTarget();
            FString Label = TEXT("CÁMARA LIBRE");
            if (Target == Pawn) Label = TEXT("SIGUIENDO: TECJUNIOR");
            else if (const auto* Worker = Cast<AFactoryWorker>(Target)) Label = Worker->Job == TEXT("Barrera") ? TEXT("SIGUIENDO: ENCARGADO DE BARRERA") : TEXT("SIGUIENDO: EMPLEADO");
            else if (Target) Label = TEXT("SIGUIENDO");
            float TW = 0, TH = 0;
            GetTextSize(Label, TW, TH, GEngine->GetMediumFont(), .8f * S);
            const float BW = TW / S + 28, BX = W - BW - 18, BY = H - 40;
            Rect(Target ? FLinearColor(1, .54f, .12f, 1) : FLinearColor(.18f, .44f, .84f, 1), BX, BY, BW, 30);
            Text(Label, BX + 14, BY + 6, .8f, FLinearColor::White);
        }
        MuteButton = HireButton = TabButtons[0] = TabButtons[1] = FBox2D(ForceInit);
        // The info panel plays its entrance each time it appears.
        const bool bInfoOpen = Gathering && Gathering->bInventoryOpen && !Demo->bBuilding;
        if (bInfoOpen && !bInfoShown) InfoShownAt = GetWorld()->GetRealTimeSeconds();
        bInfoShown = bInfoOpen;
        DrawMoney(S, W, H);
        DrawEvents(S, W, H);
        DrawNpcSpeech(S, W, H);
        DrawGuide(S, W, H);
        DrawMissionNotice(S, W, H);
        DrawBoothPanel(S, W, H);
        if (Gathering && Gathering->bInventoryOpen && !Demo->bBuilding) DrawCharacterPanel(S, W, H);
        return;
    }
    // Match InteractMachine: E goes to a reachable pile only when it is closer.
    const bool bPileIsPrimary = Gathering && Gathering->FocusedPile &&
        (!Demo->FocusedBuilding || FVector::DistSquared2D(Pawn->GetActorLocation(),Gathering->FocusedPile->GetActorLocation()) <
            FVector::DistSquared2D(Pawn->GetActorLocation(),Demo->FocusedBuilding->GetActorLocation()));
    const float InventoryHeight = 88 + 25 * Factory->Resources.Num();
    Box(24,24,306,InventoryHeight);
    Rect(Cyan,24,24,306,2);
    Text(TEXT("ROBOT / CARGA"),42,39,1.0f,Cyan);
    RightText(TEXT("[I] Detalle"),312,42,.78f,Muted);
    float ItemY = 68;
    for (UFactoryResourceDefinition* Item : Factory->Resources)
    {
        if (!Item) continue;
        Rect(Item->Color,42,ItemY+4,8,8);
        Text(Item->DisplayName.ToString(),61,ItemY,.95f,White);
        RightText(FString::FromInt(Inventory->GetQuantity(Item->ItemId)),312,ItemY,1.0f,White);
        ItemY += 25;
    }
    Bar(42,ItemY+5,270,4,Inventory->GetTotal()/float(FMath::Max(Inventory->Capacity,1)),Inventory->GetFreeSpace()>0 ? Cyan : Amber);
    Text(FString::Printf(TEXT("MOCHILA  %d / %d"),Inventory->GetTotal(),Inventory->Capacity),42,ItemY+15,.75f,Muted);
    const bool bGoal = Factory->GoalComplete();
    const int32 Stored = Factory->StoredPlates();
    if (Factory->bEnableSiteProgress)
    {
        const float X=W-398;
        const int32 Stage=FMath::Clamp(Factory->SiteStage,0,3);
        const bool bSiteComplete=Stage>=3;
        const bool bRevealing=!bSiteComplete && Factory->SiteTransitionRemaining>0.0f;
        Box(X,24,374,257);
        Rect(bGoal ? Cyan : Amber,X,24,374,2);
        FitText(bGoal ? TEXT("PRIMERA FÁBRICA COMPLETADA") : TEXT("OBJETIVO / AUTOMATIZAR PLACAS"),X+20,40,334,.94f,bGoal ? Cyan : Amber);
        Text(FString::Printf(TEXT("%02d / 20"),Stored),X+20,67,1.32f,White);
        RightText(FString::Printf(TEXT("%02d / 20"),Factory->PlatesDelivered),X+354,67,1.32f,White);
        Text(TEXT("PLACAS EN DEPÓSITOS"),X+20,95,.75f,Muted);
        RightText(TEXT("ENTREGADAS POR CINTA"),X+354,95,.75f,Muted);
        Bar(X+20,113,155,4,Stored/20.0f,Cyan);
        Bar(X+199,113,155,4,Factory->PlatesDelivered/20.0f,Cyan);
        Rect(Border,X+20,133,334,1);

        Text(TEXT("ANEXO / PORTÓN FRONTAL"),X+20,148,.78f,White);
        RightText(FString::Printf(TEXT("%d / 3"),Stage),X+354,146,.86f,bSiteComplete ? Cyan : Muted);
        const TCHAR* Labels[]={TEXT("1 TALLER"),TEXT("2 CARGA"),TEXT("3 EXPANSIÓN")};
        const float MarkerW=(334.0f-12.0f)/3.0f;
        for (int32 Index=0;Index<3;++Index)
        {
            const bool bBuilt=Stage>=Index+1;
            const bool bNext=Stage==Index;
            const FLinearColor Color=bBuilt ? Cyan : bNext ? Amber : Muted;
            const float MarkerX=X+20+Index*(MarkerW+6);
            Rect(Recess,MarkerX,173,MarkerW,24);
            Rect(bBuilt || (bNext && bRevealing) ? Color : Border,MarkerX,173,MarkerW,2);
            FitText(Labels[Index],MarkerX+7,181,MarkerW-14,.76f,Color);
        }

        if (bSiteComplete)
        {
            FitText(Factory->SiteStageName(3)+TEXT(" habilitado"),X+20,212,334,.92f,Cyan);
            Text(TEXT("36 celdas nuevas y conexión por cintas"),X+20,238,.78f,Muted);
            Bar(X+20,261,334,4,1.0f,Cyan);
        }
        else
        {
            const int32 Target=Factory->SiteNextTarget();
            const int32 Progress=Factory->SiteCurrentProgress();
            const FString Prefix=bRevealing ? TEXT("REVELANDO: ") : TEXT("PRÓXIMO: ");
            FitText(Prefix+Factory->SiteStageName(Stage+1),X+20,212,334,.88f,bRevealing ? Cyan : White);
            const FString Requirement=FString::Printf(TEXT("%d / %d placas %s"),Progress,Target,
                Stage==0 ? TEXT("producidas") : TEXT("entregadas por cinta"));
            FitText(Requirement,X+20,238,bRevealing ? 276.0f : 334.0f,.76f,Muted);
            if (bRevealing)
                RightText(FString::Printf(TEXT("%.1f s"),FMath::Clamp(Factory->SiteTransitionRemaining,0.0f,2.0f)),X+354,238,.78f,Cyan);
            const float Fraction=bRevealing ? 1.0f-Factory->SiteTransitionRemaining/2.0f : Progress/float(FMath::Max(Target,1));
            Bar(X+20,261,334,4,Fraction,bRevealing ? Cyan : Amber);
        }
    }
    else
    {
        Box(W-398,24,374,145);
        Rect(bGoal ? Cyan : Amber,W-398,24,374,2);
        Text(bGoal ? TEXT("PRIMERA FÁBRICA COMPLETADA") : TEXT("OBJETIVO / AUTOMATIZAR PLACAS"),W-378,40,.95f,bGoal ? Cyan : Amber);
        Text(FString::Printf(TEXT("%02d / 20"),Stored),W-378,68,1.65f,White);
        RightText(TEXT("PLACAS EN DEPÓSITOS"),W-44,79,.75f,Muted);
        Bar(W-378,103,334,6,Stored/20.0f,Cyan);
        Text(bGoal ? TEXT("Seguí construyendo · F5 guarda tu fábrica") : TEXT("Fundición > cinta > depósito de placas"),W-378,123,.81f,Muted);
    }

    if (Gathering && Gathering->bInventoryOpen && !Demo->bBuilding)
    {
        const float InventoryY = 24 + InventoryHeight + 14;
        Box(24,InventoryY,306,96+47*Factory->Resources.Num());
        Text(TEXT("INVENTARIO"),42,InventoryY+17,1.1f,White);
        Text(TEXT("E recoger / cargar · F retirar"),42,InventoryY+43,.8f,Muted);
        float Y = InventoryY+75;
        for (UFactoryResourceDefinition* Item : Factory->Resources)
        {
            if (!Item) continue;
            Rect(Recess,42,Y,270,39);
            Rect(Item->Color,42,Y,3,39);
            Text(Item->DisplayName.ToString(),57,Y+9,.98f,White);
            RightText(FString::FromInt(Inventory->GetQuantity(Item->ItemId)),299,Y+9,1.0f,White);
            Y+=47;
        }
    }

    // The yard stays readable; extra labels appear only while planning a layout.
    for (AFactoryBuilding* Building : Factory->Buildings())
    {
        if (Building->Definition->Kind == EFactoryBuildingKind::Belt || (!Demo->bBuilding && Building!=Demo->FocusedBuilding)) continue;
        FVector2D Screen;
        if (!PlayerOwner->ProjectWorldLocationToScreen(Building->GetActorLocation()+FVector(0,0,185),Screen)) continue;
        const float X = Screen.X/S, Y = Screen.Y/S;
        if (X<80 || X>W-80 || Y<185 || Y>H-180) continue;
        if (Factory->bEnableSiteProgress && X+77>W-398 && Y-10<281) continue;
        Rect(Panel,X-77,Y-10,154,40);
        Rect(Building==Demo->FocusedBuilding ? Amber : Cyan,X-77,Y-10,2,40);
        Text(Building->Definition->DisplayName.ToString(),X-65,Y-5,.88f,Building==Demo->FocusedBuilding ? Amber : White);
        Text(FString::Printf(TEXT("%d unidades"),Building->StoredTotal()),X-65,Y+13,.73f,Muted);
    }

    CatalogButtons.Empty();
    if (Demo->bBuilding)
    {
        const int32 Count = Factory->Catalog.Num();
        const float CardW = 158, Gap = 8, StartX = (W-(CardW+Gap)*Count+Gap)/2;
        const float Y = H-172;
        for (int32 Index=0;Index<Count;++Index)
        {
            auto* Entry = Factory->Catalog[Index].Get();
            const float X = StartX+Index*(CardW+Gap);
            CatalogButtons.Add(FBox2D(FVector2D(X*S,Y*S),FVector2D((X+CardW)*S,(Y+93)*S)));
            if (!Entry) continue;
            const bool bSelected = Index==Demo->SelectedIndex;
            Box(X,Y,CardW,93);
            Rect(bSelected ? Cyan : Border,X,Y,CardW,bSelected ? 3 : 1);
            Rect(bSelected ? FLinearColor(.035f,.14f,.14f,1) : Recess,X+10,Y+15,22,23);
            Text(FString::FromInt(Index+1),X+17,Y+19,.85f,bSelected ? Cyan : Muted);
            Text(Entry->DisplayName.ToString(),X+40,Y+19,.88f,bSelected ? Cyan : White);
            Text(FString::Printf(TEXT("%d chatarra"),Entry->ScrapCost),X+12,Y+47,.98f,Inventory->GetQuantity(TEXT("Scrap"))>=Entry->ScrapCost ? Amber : Red);
            Text(Entry->Kind==EFactoryBuildingKind::Belt ? TEXT("Recta > flecha") : TEXT("Entrada > salida"),X+12,Y+72,.76f,Muted);
        }
        const FString Status = Demo->PlacementMessage;
        Box((W-720)/2,H-226,720,40);
        Rect(Demo->bPreviewValid ? Cyan : Red,(W-720)/2,H-226,3,40);
        Text(Status,(W-690)/2,H-215,.92f,Demo->bPreviewValid ? Cyan : Red);
    }
    else if (Demo->FocusedBuilding)
    {
        auto* Building = Demo->FocusedBuilding.Get();
        auto* Definition = Building->Definition.Get();
        const float X=W-398,Y=H-349;
        Box(X,Y,374,265);
        Rect(Amber,X,Y,374,2);
        Text(Definition->DisplayName.ToString(),X+20,Y+17,1.25f,White);
        const bool bBlocked = Definition->Kind==EFactoryBuildingKind::Processor ? Building->Output->GetFreeSpace()<Definition->OutputQuantity :
            Definition->Kind==EFactoryBuildingKind::Storage ? Building->Input->GetFreeSpace()==0 :
            Building->StateText==TEXT("Salida bloqueada") || Building->StateText==TEXT("Salida sin conectar");
        const bool bWorking = (Definition->Kind==EFactoryBuildingKind::Processor && !bBlocked && Building->Input->GetQuantity(Definition->InputItem)>=Definition->InputQuantity) ||
            (Definition->Kind==EFactoryBuildingKind::Belt && Building->StateText==TEXT("Transportando"));
        const FLinearColor StateColor = bBlocked ? Amber : (bWorking || Building->StoredTotal()>0 ? Cyan : Muted);
        Rect(Recess,X+20,Y+48,334,25);
        Rect(StateColor,X+29,Y+57,7,7);
        Text(Building->StateText.Replace(TEXT(" · E para cargar"),TEXT("")),X+44,Y+52,.85f,StateColor);
        if (Definition->Kind==EFactoryBuildingKind::Processor)
        {
            Text(FString::Printf(TEXT("%d %s  >  %d %s"),Definition->InputQuantity,*Name(Definition->InputItem),Definition->OutputQuantity,*Name(Definition->OutputItem)),X+20,Y+88,.83f,White);
            Text(FString::Printf(TEXT("Entrada %d / %d    Salida %d / %d"),Building->Input->GetTotal(),Building->Input->Capacity,Building->Output->GetTotal(),Building->Output->Capacity),X+20,Y+115,.84f,Muted);
            Bar(X+20,Y+144,334,6,Building->ProgressSeconds/FMath::Max(Definition->CycleSeconds,.1f),StateColor);
        }
        else
        {
            Text(FString::Printf(TEXT("Contenido  %d / %d"),Building->Input->GetTotal(),Building->Input->Capacity),X+20,Y+87,1.0f,White);
            FString Contents;
            for (UFactoryResourceDefinition* Item : Factory->Resources) if (Item && Building->Input->GetQuantity(Item->ItemId)>0)
                Contents+=FString::Printf(TEXT("%s %d  "),*Item->DisplayName.ToString(),Building->Input->GetQuantity(Item->ItemId));
            Text(Contents,X+20,Y+111,.80f,Muted);
            Bar(X+20,Y+135,334,4,Building->Input->GetTotal()/float(FMath::Max(Building->Input->Capacity,1)),StateColor);
            if (Definition->Kind==EFactoryBuildingKind::Storage)
                Text(TEXT("Filtro: ")+Name(Building->StorageItem)+TEXT(" · G cambia (vacío)"),X+20,Y+148,.75f,Amber);
        }
        Text(Building->bConnected ? TEXT("Salida conectada") : TEXT("Salida libre · alineá una cinta"),X+20,Y+172,.82f,Building->bConnected ? Cyan : Muted);
        Rect(Border,X+20,Y+197,334,1);
        Text(bPileIsPrimary ? TEXT("[F] Retirar de esta máquina") : TEXT("[E] Cargar       [F] Retirar"),X+20,Y+209,.98f,White);
        Text(TEXT("[X] Desmontar y recuperar contenido"),X+20,Y+237,.82f,Muted);
    }
    if (!Demo->bBuilding && bPileIsPrimary)
    {
        Box((W-450)/2,H-158,450,68);
        Rect(Cyan,(W-450)/2,H-158,3,68);
        Text(TEXT("[ E ] RECOGER CHATARRA"),(W-410)/2,H-143,1.1f,Cyan);
        Text(FString::Printf(TEXT("%d unidades · espacio libre %d"),Gathering->FocusedPile->Amount,Inventory->GetFreeSpace()),(W-410)/2,H-115,.83f,Muted);
    }
    else if (!bGoal && !Demo->bBuilding && !Demo->FocusedBuilding)
    {
        Box((W-580)/2,H-147,580,53);
        Text(TEXT("E: recoger chatarra  >  B + 4: colocar cintas"),(W-548)/2,H-136,.91f,White);
        Text(TEXT("Después cargá el depósito de entrada con E."),(W-548)/2,H-116,.8f,Muted);
    }
    FString Message;
    if (Demo->NotificationUntil>GetWorld()->GetTimeSeconds()) Message=Demo->Notification;
    else if (Gathering && Gathering->NotificationUntil>GetWorld()->GetTimeSeconds()) Message=Gathering->Notification;
    if (!Message.IsEmpty())
    {
        const float NoticeY = 24+InventoryHeight+14;
        Box((W-720)/2,NoticeY,720,39);
        Rect(Cyan,(W-720)/2,NoticeY,3,39);
        Text(Message,(W-690)/2,NoticeY+10,.92f,Cyan);
    }
    Rect(Panel,0,H-64,W,64);
    Rect(Border,0,H-64,W,1);
    Text(TEXT("WASD Mover   SHIFT Rápido   E Recoger / cargar   F Retirar   B Construir   I Inventario"),24,H-51,.92f,White);
    Text(TEXT("R Girar   Clic Colocar   Der. Cancelar   X Desmontar   Rueda Zoom   Central Desplazar   Arrastrar Der. Orbitar   Inicio Centrar   F5/F9 Guardar/Cargar"),24,H-26,.76f,Muted);
}

void AFactoryDemoHUD::DrawBeltDetail(float S, float W)
{
    AFactoryDispatchBelt* Belt = nullptr;
    for (TActorIterator<AFactoryDispatchBelt> It(GetWorld()); It; ++It)
        if (It->bDetailOpen) { Belt = *It; break; }
    if (!Belt) return;
    const FLinearColor Panel(.012f,.023f,.032f,.94f), Border(.055f,.10f,.12f,1), White(.93f,.96f,.97f,1);
    const FLinearColor Muted(.60f,.70f,.74f,1), Red(1,.30f,.26f,1), Recess(.022f,.042f,.052f,.96f);
    auto Rect = [&](FLinearColor Color, float X, float Y, float Width, float Height) { DrawRect(Color, X*S, Y*S, Width*S, Height*S); };
    auto Text = [&](const FString& Value, float X, float Y, float Scale, FLinearColor Color) { DrawText(Value, Color, X*S, Y*S, GEngine->GetMediumFont(), Scale*S); };
    const float X = W - 398, Y = 24, Width = 374;
    Rect(FLinearColor(0,0,0,.18f),X+3,Y+4,Width,196);
    Rect(Border,X,Y,Width,196);
    Rect(Panel,X+1,Y+1,Width-2,194);
    Rect(Red,X,Y,Width,3);
    Text(FString::Printf(TEXT("%s  ·  LLENA"), *Belt->BeltName),X+20,Y+18,1.1f,Red);
    // The boxes pack loosely, so how many fit varies: the detail (shown only when full) gives the count.
    Text(FString::Printf(TEXT("Cajas en la cinta   %d"), Belt->GetBoxCount()),X+20,Y+54,.95f,White);
    Rect(Recess,X+20,Y+82,Width-40,6);
    Rect(Red,X+20,Y+82,Width-40,6);
    Text(TEXT("Estado   detenida"),X+20,Y+102,.88f,White);
    Text(TEXT("No queda lugar al final de la cinta:"),X+20,Y+130,.8f,Muted);
    Text(TEXT("la máquina dejó de despachar cajas."),X+20,Y+150,.8f,Muted);
    Text(TEXT("Clic en el cartel para cerrar"),X+20,Y+174,.72f,Muted);
}
