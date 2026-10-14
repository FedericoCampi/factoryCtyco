#include "GrowEvolution.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"

bool AGrowEvolutionHUD::Click(float X, float Y)
{
    const auto* Controller = Cast<AGrowPlayerController>(PlayerOwner);
    AGrowEvolutionWorld* World = Controller ? Controller->Evolution() : nullptr;
    if (!World) return false;

    const FVector2D Position(X, Y);
    const bool bReady = !World->bResolving && World->TransitionRemaining <= 0.0f;
    if (UndoButton.IsInside(Position))
    {
        World->UndoDecision();
        return true;
    }
    if (ResetButton.IsInside(Position))
    {
        World->ResetEvolution();
        return true;
    }
    for (int32 Index = 0; Index < DecisionButtons.Num(); ++Index)
    {
        if (!DecisionButtons[Index].IsInside(Position)) continue;
        const EGrowDecision Decision = static_cast<EGrowDecision>(Index);
        if (bReady && !World->IsComplete() && !World->HasDecision(Decision)) World->ChooseDecision(Decision);
        return true;
    }
    return false;
}

void AGrowEvolutionHUD::DrawHUD()
{
    Super::DrawHUD();
    DecisionButtons.Reset();
    UndoButton = FBox2D(ForceInit);
    ResetButton = FBox2D(ForceInit);

    const auto* Controller = Cast<AGrowPlayerController>(PlayerOwner);
    const AGrowEvolutionWorld* World = Controller ? Controller->Evolution() : nullptr;
    if (!Canvas || !GEngine || !World) return;

    const float S = FMath::Clamp(FMath::Min(Canvas->SizeX / 1440.0f, Canvas->SizeY / 900.0f), .5f, 1.8f);
    const float W = Canvas->SizeX / S;
    const float H = Canvas->SizeY / S;
    const FLinearColor Panel(.015f, .025f, .034f, .96f);
    const FLinearColor Recess(.027f, .045f, .056f, 1);
    const FLinearColor Border(.090f, .140f, .163f, 1);
    const FLinearColor White(.94f, .97f, .98f, 1);
    const FLinearColor Muted(.61f, .71f, .76f, 1);
    const FLinearColor Quiet(.38f, .48f, .53f, 1);
    const FLinearColor Mint(.32f, .91f, .77f, 1);
    const FLinearColor HudAmber(1.0f, .70f, .34f, 1);
    const bool bResolving = World->bResolving;
    const bool bWaiting = bResolving || World->TransitionRemaining > 0.0f;
    const float UpgradeDelay = FMath::Max(World->UpgradeDelaySeconds, .1f);
    const float Countdown = FMath::Clamp(World->EvolutionCountdown, 0.0f, UpgradeDelay);
    const float UpgradeProgress = 1.0f - Countdown / UpgradeDelay;
    const FLinearColor PendingColor = AGrowEvolutionWorld::DecisionColor(World->PendingDecision);
    const bool bComplete = World->IsComplete();
    const bool bAwake = World->HasDecision(EGrowDecision::Awaken);
    const bool bSuccessful = bComplete && World->IsSuccessful();
    const int32 Turn = FMath::Clamp(World->History.Num(), 0, 6);

    float MouseX = -1, MouseY = -1;
    PlayerOwner->GetMousePosition(MouseX, MouseY);
    const FVector2D Mouse(MouseX, MouseY);
    auto Rect = [&](FLinearColor Color, float X, float Y, float Width, float Height)
    {
        DrawRect(Color, X * S, Y * S, Width * S, Height * S);
    };
    auto Text = [&](const FString& Value, float X, float Y, float Scale, FLinearColor Color)
    {
        DrawText(Value, Color, X * S, Y * S, GEngine->GetMediumFont(), Scale * S);
    };
    auto WidthOf = [&](const FString& Value, float Scale)
    {
        float Width = 0, Height = 0;
        GetTextSize(Value, Width, Height, GEngine->GetMediumFont(), Scale * S);
        return Width / S;
    };
    auto FitText = [&](const FString& Value, float X, float Y, float Width, float Scale, FLinearColor Color)
    {
        const float Measured = WidthOf(Value, Scale);
        Text(Value, X, Y, Measured > Width ? Scale * Width / FMath::Max(Measured, 1.0f) : Scale, Color);
    };
    auto Wrap = [&](const FString& Value, float X, float Y, float Width, float Scale, float LineHeight, int32 MaxLines, FLinearColor Color)
    {
        TArray<FString> Words;
        Value.ParseIntoArrayWS(Words);
        TArray<FString> WrappedLines;
        FString Line;
        for (const FString& Word : Words)
        {
            const FString Candidate = Line.IsEmpty() ? Word : Line + TEXT(" ") + Word;
            if (!Line.IsEmpty() && WidthOf(Candidate, Scale) > Width)
            {
                WrappedLines.Add(Line);
                Line = Word;
            }
            else Line = Candidate;
        }
        if (!Line.IsEmpty()) WrappedLines.Add(Line);
        const int32 Count = FMath::Min(MaxLines, WrappedLines.Num());
        for (int32 Index = 0; Index < Count; ++Index)
        {
            FString Display = WrappedLines[Index];
            if (Index == MaxLines - 1 && WrappedLines.Num() > MaxLines)
            {
                while (!Display.IsEmpty() && WidthOf(Display + TEXT("..."), Scale) > Width) Display.LeftChopInline(1);
                Display += TEXT("...");
            }
            FitText(Display, X, Y + Index * LineHeight, Width, Scale, Color);
        }
        return Y + Count * LineHeight;
    };
    auto Box = [&](float X, float Y, float Width, float Height, FLinearColor Edge)
    {
        Rect(FLinearColor(0, 0, 0, .20f), X + 3, Y + 4, Width, Height);
        Rect(Edge, X, Y, Width, Height);
        Rect(Panel, X + 1, Y + 1, Width - 2, Height - 2);
    };
    auto Bounds = [&](float X, float Y, float Width, float Height)
    {
        return FBox2D(FVector2D(X * S, Y * S), FVector2D((X + Width) * S, (Y + Height) * S));
    };
    auto Segments = [&](float X, float Y, float Width, float Height, int32 Level, int32 Maximum, FLinearColor Color)
    {
        const float Gap = 5;
        const float SegmentWidth = (Width - (Maximum - 1) * Gap) / Maximum;
        for (int32 Index = 0; Index < Maximum; ++Index)
            Rect(Index < Level ? Color : Border, X + Index * (SegmentWidth + Gap), Y, SegmentWidth, Height);
    };

    // Keep decisions at the screen edge; the evolving world remains unobstructed.
    Box(24, 24, W - 48, 95, Border);
    Rect(Mint, 24, 24, 4, 95);
    FitText(TEXT("ROBOTS / MUNDO EN EVOLUCIÓN"), 44, 42, W - 652, 1.15f, White);
    const FString Reaction = World->PendingSource == World->PendingDecision ? AGrowEvolutionWorld::DecisionName(World->PendingDecision) :
        AGrowEvolutionWorld::DecisionName(World->PendingSource) + TEXT(" > ") + AGrowEvolutionWorld::DecisionName(World->PendingDecision);
    const FString Instruction = bResolving ? TEXT("Reacción en cadena: ") + Reaction :
        bWaiting ? TEXT("El escenario toma forma. Observá cómo cambian sus conexiones.") :
        bComplete ? TEXT("La secuencia terminó. Probá otro orden para descubrir otro futuro.") :
        TEXT("Elegí un sistema. Sus conexiones pueden hacer evolucionar a los demás.");
    FitText(Instruction, 44, 81, W - 652, .83f, Muted);

    const float StageX = W - 566;
    Text(TEXT("ETAPA"), StageX, 44, .80f, Muted);
    Text(FString::Printf(TEXT("%d / 6"), Turn), StageX + 82, 39, 1.25f, White);
    Segments(StageX, 77, 151, 6, Turn, 6, Mint);
    FitText(bResolving ? FString::Printf(TEXT("PRÓXIMO NIVEL EN %.1f s"), Countdown) :
        bWaiting ? TEXT("TRANSFORMANDO...") : bComplete ? TEXT("SECUENCIA COMPLETA") : TEXT("UNA DECISIÓN POR TURNO"),
        StageX, 94, 151, .59f, bResolving ? PendingColor : Muted);

    UndoButton = Bounds(W - 375, 43, 190, 39);
    ResetButton = Bounds(W - 173, 43, 129, 39);
    const bool bCanRewind = Turn > 0 || bResolving;
    auto ActionButton = [&](const FBox2D& Button, const FString& Label)
    {
        const bool bHovered = bCanRewind && Button.IsInside(Mouse);
        const float X = Button.Min.X / S, Y = Button.Min.Y / S;
        const float Width = Button.GetSize().X / S;
        Rect(bHovered ? FLinearColor(.055f, .13f, .14f, 1) : Recess, X, Y, Width, 39);
        Rect(bHovered ? Mint : Border, X, Y + 38, Width, 1);
        FitText(Label, X + 12, Y + 11, Width - 24, .82f, bCanRewind ? White : Quiet);
    };
    ActionButton(UndoButton, TEXT("Deshacer [Retroceso]"));
    ActionButton(ResetButton, TEXT("Reiniciar [R]"));
    Text(bResolving ? TEXT("Podés deshacer o reiniciar durante la reacción.") : TEXT("Explorá combinaciones sin perder tu secuencia."),
        W - 375, 95, .66f, Muted);

    const float SideX = W - 316;
    const float SideY = 141;
    const float SideW = 292;
    const FLinearColor RoleColor = bAwake ? AGrowEvolutionWorld::ProfessionColor(World->Profession) : Mint;
    Box(SideX, SideY, SideW, 462, Border);
    Rect(bComplete ? (bSuccessful ? Mint : HudAmber) : RoleColor, SideX, SideY, SideW, 3);
    Text(bComplete ? TEXT("TU MUNDO / RESULTADO") : TEXT("LA COLONIA"), SideX + 18, SideY + 20, .93f, White);
    Text(bAwake ? TEXT("PROFESIÓN ACTUAL") : TEXT("ROBOTS EN REPOSO"), SideX + 18, SideY + 58, .68f, Muted);
    FitText(bAwake ? AGrowEvolutionWorld::ProfessionName(World->Profession) : TEXT("Un futuro por despertar"),
        SideX + 18, SideY + 79, SideW - 36, 1.16f, bAwake ? RoleColor : White);
    Text(TEXT("NIVEL DE COLONIA"), SideX + 18, SideY + 121, .70f, Muted);
    Text(FString::Printf(TEXT("%d / 3"), World->CreatureLevel), SideX + SideW - 67, SideY + 115, 1.0f, bAwake ? RoleColor : Quiet);
    Segments(SideX + 18, SideY + 145, SideW - 36, 7, FMath::Clamp(World->CreatureLevel, 0, 3), 3, RoleColor);
    Text(FString::Printf(TEXT("%d CONEXIONES ACTIVAS"), World->ActiveLinks), SideX + 18, SideY + 160, .60f, Muted);
    Rect(Border, SideX + 18, SideY + 175, SideW - 36, 1);

    if (bResolving)
    {
        FitText(TEXT("EVOLUCIONA: ") + AGrowEvolutionWorld::DecisionName(World->PendingDecision).ToUpper(),
            SideX + 18, SideY + 195, SideW - 36, .83f, PendingColor);
        Wrap(World->PendingReason, SideX + 18, SideY + 222, SideW - 36, .81f, 17, 3, White);
        Text(TEXT("PRÓXIMO NIVEL"), SideX + 18, SideY + 284, .70f, Muted);
        Text(FString::Printf(TEXT("%.1f s"), Countdown), SideX + SideW - 77, SideY + 279, 1.02f, PendingColor);
        Rect(Border, SideX + 18, SideY + 306, SideW - 36, 5);
        Rect(PendingColor, SideX + 18, SideY + 306, (SideW - 36) * UpgradeProgress, 5);
        Text(FString::Printf(TEXT("%d mejoras pendientes"), World->PendingUpgradeCount), SideX + 18, SideY + 316, .60f, Muted);
    }
    else if (bComplete)
    {
        FitText(bSuccessful ? TEXT("COLONIA EN PLENITUD") : TEXT("OTRO FUTURO ES POSIBLE"),
            SideX + 18, SideY + 195, SideW - 36, .90f, bSuccessful ? Mint : HudAmber);
        Wrap(World->OutcomeText(), SideX + 18, SideY + 222, SideW - 36, .85f, 19, bSuccessful ? 5 : 2, White);
        if (!bSuccessful)
            Wrap(World->ProgressHint(), SideX + 18, SideY + 274, SideW - 36, .78f, 17, 3, HudAmber);
    }
    else if (!bAwake)
    {
        Text(TEXT("SI DESPERTÁS AHORA"), SideX + 18, SideY + 195, .70f, Mint);
        Wrap(World->PreviewProfession(), SideX + 18, SideY + 220, SideW - 36, .99f, 21, 2, White);
        Wrap(World->ProgressHint(), SideX + 18, SideY + 273, SideW - 36, .78f, 18, 3, Muted);
    }
    else
    {
        Text(World->CreatureLevel >= 3 ? TEXT("EVOLUCIÓN COMPLETA") : TEXT("PRÓXIMA EVOLUCIÓN"),
            SideX + 18, SideY + 195, .70f, RoleColor);
        Wrap(World->ProgressHint(), SideX + 18, SideY + 222, SideW - 36, .85f, 19, 5, White);
    }
    Rect(Border, SideX + 18, SideY + 331, SideW - 36, 1);
    Text(TEXT("ÚLTIMO CAMBIO"), SideX + 18, SideY + 350, .70f, Muted);
    Wrap(World->LastEvent.IsEmpty() ? TEXT("El mundo espera tu primera decisión.") : World->LastEvent,
        SideX + 18, SideY + 375, SideW - 36, .82f, 18, 4, White);

    // Each occupied slot records the actual order, so rewinding is easy to read.
    const float SequenceY = H - 247;
    Text(TEXT("TU SECUENCIA"), 26, SequenceY + 10, .77f, Muted);
    const float SequenceX = 169;
    const float SequenceGap = 8;
    const float SequenceW = (W - SequenceX - 24 - 5 * SequenceGap) / 6;
    for (int32 Index = 0; Index < 6; ++Index)
    {
        const float X = SequenceX + Index * (SequenceW + SequenceGap);
        const bool bChosen = World->History.IsValidIndex(Index);
        const FLinearColor Color = bChosen ? AGrowEvolutionWorld::DecisionColor(World->History[Index]) : Quiet;
        Rect(Recess, X, SequenceY, SequenceW, 35);
        Rect(Color, X, SequenceY, 2, 35);
        Text(FString::FromInt(Index + 1), X + 10, SequenceY + 10, .72f, Color);
        FitText(bChosen ? AGrowEvolutionWorld::DecisionName(World->History[Index]) : TEXT("Por decidir"),
            X + 30, SequenceY + 9, SequenceW - 40, .76f, bChosen ? White : Quiet);
    }

    const float CardGap = 10;
    const float CardW = (W - 48 - 5 * CardGap) / 6;
    const float CardY = H - 194;
    const float CardH = 146;
    int32 HoveredIndex = INDEX_NONE;
    for (int32 Index = 0; Index < 6; ++Index)
    {
        const EGrowDecision Decision = static_cast<EGrowDecision>(Index);
        const bool bChosen = World->HasDecision(Decision);
        const bool bAvailable = !bWaiting && !bComplete && !bChosen;
        const bool bPending = bResolving && World->PendingUpgradeCount > 0 && World->PendingDecision == Decision;
        const float X = 24 + Index * (CardW + CardGap);
        const FBox2D Button = Bounds(X, CardY, CardW, CardH);
        DecisionButtons.Add(Button);
        const bool bInspected = Button.IsInside(Mouse);
        const bool bHovered = bAvailable && bInspected;
        if (bInspected) HoveredIndex = Index;
        const FLinearColor Color = AGrowEvolutionWorld::DecisionColor(Decision);
        Box(X, CardY, CardW, CardH, bInspected || bPending ? Color : Border);
        Rect(bChosen || bHovered || bPending ? Color : Border, X, CardY, CardW, bHovered || bPending ? 4 : 2);
        Rect(bHovered || bPending ? FLinearColor(Color.R * .20f, Color.G * .20f, Color.B * .20f, 1) : Recess,
            X + 13, CardY + 15, 26, 26);
        Text(FString::FromInt(Index + 1), X + 21, CardY + 20, .82f, bAvailable || bChosen ? Color : Quiet);
        FitText(AGrowEvolutionWorld::DecisionName(Decision), X + 49, CardY + 21, CardW - 61, 1.00f, bChosen || bAvailable ? White : Muted);
        Wrap(AGrowEvolutionWorld::DecisionDescription(Decision), X + 14, CardY + 56, CardW - 28, .76f, 17, 2, Muted);
        Rect(Border, X + 14, CardY + 102, CardW - 28, 1);
        if (bPending)
        {
            const int32 Level = FMath::Clamp(World->DecisionLevel(Decision), 0, 3);
            FitText(FString::Printf(TEXT("NIVEL %d > %d"), Level, FMath::Min(Level + 1, 3)),
                X + 14, CardY + 112, CardW - 80, .68f, Color);
            Text(FString::Printf(TEXT("%.1f s"), Countdown), X + CardW - 57, CardY + 111, .76f, Color);
            Rect(Border, X + 14, CardY + 132, CardW - 28, 4);
            Rect(Color, X + 14, CardY + 132, (CardW - 28) * UpgradeProgress, 4);
        }
        else if (bChosen)
        {
            const int32 Level = FMath::Clamp(World->DecisionLevel(Decision), 0, 3);
            Text(FString::Printf(TEXT("NIVEL %d"), Level), X + 14, CardY + 116, .72f, Color);
            Segments(X + CardW - 87, CardY + 121, 73, 5, Level, 3, Color);
        }
        else
        {
            Text(bResolving ? TEXT("ESPERANDO REACCIÓN") : bWaiting ? TEXT("TRANSFORMANDO...") : bHovered ? TEXT("ELEGIR ESTE SISTEMA") : TEXT("ELEGIR"),
                X + 14, CardY + 116, .70f, bAvailable ? Color : Quiet);
            if (bAvailable) Text(TEXT(">"), X + CardW - 25, CardY + 113, .92f, Color);
        }
    }
    if (HoveredIndex != INDEX_NONE)
    {
        const EGrowDecision Inspected = static_cast<EGrowDecision>(HoveredIndex);
        const FLinearColor Color = AGrowEvolutionWorld::DecisionColor(Inspected);
        Rect(Panel, 24, H - 288, W - 48, 31);
        Rect(Color, 24, H - 288, 3, 31);
        FitText(AGrowEvolutionWorld::DecisionName(Inspected) + TEXT(": ") + World->SystemHint(Inspected),
            38, H - 280, W - 76, .78f, White);
    }
    FitText(TEXT("[1–6] Elegir   ·   Pasá el cursor para ver conexiones y requisitos   ·   Cada sistema se usa una vez"),
        25, H - 28, W - 385, .72f, Muted);
    FitText(TEXT("Rueda: zoom   ·   Inicio: centrar"), W - 339, H - 28, 315, .72f, Muted);
}
