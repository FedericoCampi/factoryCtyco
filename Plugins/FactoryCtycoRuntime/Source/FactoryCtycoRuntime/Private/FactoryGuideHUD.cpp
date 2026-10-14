// The guide on the HUD (AFactoryGuide): the story cards and mission briefing that cover the screen at the start,
// then the objective card (top left, next to the events sign) and an arrow on the screen edge when the big
// 3D arrow's target is out of view. Same "Pegatina Pop" look as the info panel (FactoryHudDraw.h).
#include "FactoryDemo.h"
#include "FactoryEconomy.h"
#include "FactoryGuide.h"
#include "FactoryCameraComponent.h"
#include "FactoryHudDraw.h"
#include "FactoryGathering.h"
#include "UObject/UObjectIterator.h"
#include "Components/TextRenderComponent.h"
#include "FactoryMission.h"
#include "FactoryNpc.h"
#include "EngineUtils.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"

using namespace FactoryHudDraw;

namespace
{
    const FLinearColor GCream = Hex(0xFFF4E0), GOrange = Hex(0xFF8A1F), GInk = Hex(0x2B2340), GGreen = Hex(0x3DD68C),
        GMuted = Hex(0x5A4E6E), GNight = Hex(0x120E1C);

    TArray<FString> GuideLines(const FString& Text)
    {
        TArray<FString> Out;
        Text.ParseIntoArray(Out, TEXT("\n"), false);
        return Out;
    }

    /** "Press to go on" chip, breathing, centred on CX. */
    void GuideContinueChip(const FPen& Pen, const FString& Label, float CX, float Y, float T, float Alpha)
    {
        const float Breathe = 1.0f + .04f * FMath::Sin(T * 4.0f);
        const float CW = Pen.Width(Label, .78f) + 40;
        const FVector2D C(CX, Y + 17);
        Pen.Fill(Xf(RoundRect(CX - CW / 2 - 3, Y - 3, CW + 6, 40, 20), C, Breathe), Faded(GInk, Alpha));
        Pen.Fill(Xf(RoundRect(CX - CW / 2, Y, CW, 34, 17), C, Breathe), Faded(GOrange, Alpha));
        Pen.Centered(Label, CX, Y + 7, .78f * Breathe, Faded(FLinearColor::White, Alpha));
    }
}

bool AFactoryDemoHUD::DrawGuideCover(float S, float W, float H)
{
    const AFactoryGuide* Guide = AFactoryGuide::Find(GetWorld());
    if (!Guide) return false;
    const float Now = GetWorld()->GetRealTimeSeconds();
    // After the intro the dark cover fades away over the factory.
    const float Out = Now - Guide->GetIntroEndedAt();
    if (!Guide->IsCovering() && Out > .9f) return false;
    const float Cover = Guide->IsCovering() ? 1.0f : 1.0f - EaseOutQuart(Out / .9f);
    FPen Pen{this, Canvas, S, GEngine->GetMediumFont(), GEngine->GetLargeFont()};
    Pen.Rect(0, 0, W, H, Faded(GNight, .9f * Cover));
    if (!Guide->IsCovering()) return false;
    const float T = Now - Guide->GetShownAt();
    const FString Continue = TEXT("ESPACIO / CLIC  ·  SEGUIR");

    if (Guide->GetPhase() == AFactoryGuide::EPhase::Intro && Guide->Slides.IsValidIndex(Guide->GetSlide()))
    {
        // Story card: the kicker slides in, the title pops, the lines appear one by one.
        const FFactoryIntroSlide& Card = Guide->Slides[Guide->GetSlide()];
        const TArray<FString> Body = GuideLines(Card.Body);
        const float CW = 760, CH = 150 + 34 * Body.Num(), X = (W - CW) / 2, Y = (H - CH) / 2 - 30;
        const FVector2D Pivot(W / 2, Y + CH / 2);
        const float K = EaseOutBack(T / .45f);
        Pen.Fill(Xf(RoundRect(X + 10, Y + 10, CW, CH, 28), Pivot, K), Faded(FLinearColor::Black, .35f));
        Pen.Fill(Xf(RoundRect(X - 4, Y - 4, CW + 8, CH + 8, 32), Pivot, K), GInk);
        Pen.Fill(Xf(RoundRect(X, Y, CW, CH, 28), Pivot, K), GCream);
        const float In = Clamp01((T - .2f) / .25f), Slide = 30 * (1.0f - EaseOutQuart((T - .2f) / .4f));
        Pen.Fill(RoundRect(X + 36 - Slide, Y + 28, Pen.Width(Card.Kicker, .78f) + 28, 30, 15), Faded(GOrange, In));
        Pen.Text(Card.Kicker, X + 50 - Slide, Y + 33, .78f, Faded(FLinearColor::White, In));
        const float TitleIn = EaseOutBack((T - .35f) / .35f);
        Pen.Text(Card.Title, X + 36, Y + 72, 1.7f * FMath::Max(TitleIn, .01f), Faded(GInk, Clamp01((T - .35f) / .15f)));
        for (int32 I = 0; I < Body.Num(); ++I)
        {
            const float LineIn = Clamp01((T - .7f - .35f * I) / .3f);
            Pen.Text(Body[I], X + 36 + 16 * (1.0f - LineIn), Y + 130 + 34 * I, .95f, Faded(GMuted, LineIn));
        }
        // Progress dots: one per card, plus the briefing.
        const int32 Count = Guide->Slides.Num() + 1;
        for (int32 I = 0; I < Count; ++I)
        {
            const FVector2D D(W / 2 + (I - (Count - 1) / 2.0f) * 26, Y + CH + 40);
            Pen.Fill(Circle(D, I == Guide->GetSlide() ? 7.5f : 5.0f, 16), I <= Guide->GetSlide() ? GOrange : Faded(GCream, .35f));
        }
        GuideContinueChip(Pen, Continue, W / 2, Y + CH + 70, T, Clamp01((T - 1.0f) / .3f));
        Pen.Centered(TEXT("TAB  ·  SALTAR INTRO"), W / 2, H - 44, .7f, Faded(GCream, .45f * Clamp01((T - 1.0f) / .3f)));
        return true;
    }

    // Mission briefing: the sticker card with the ribbon, what to do and the steps ahead.
    const TArray<FString> Body = GuideLines(Guide->MissionBody);
    const int32 StepCount = Guide->Steps.Num();
    const float CW = 700, CH = 170 + 32 * Body.Num() + (StepCount ? 44 + 34 * StepCount : 0), X = (W - CW) / 2, Y = FMath::Max(30.0f, (H - CH) / 2 - 40);
    const FVector2D Pivot(W / 2, Y + CH / 2);
    const float K = EaseOutBack(T / .45f);
    Pen.Fill(Xf(RoundRect(X + 10, Y + 10, CW, CH, 28), Pivot, K), Faded(FLinearColor::Black, .35f));
    Pen.Fill(Xf(RoundRect(X - 4, Y - 4, CW + 8, CH + 8, 32), Pivot, K), GInk);
    Pen.Fill(Xf(RoundRect(X, Y, CW, CH, 28), Pivot, K), GCream);
    const float Ribbon = EaseOutBack((T - .25f) / .3f), In = Clamp01((T - .25f) / .15f);
    const float RW = CW - 120, RX = X + 60;
    Pen.Fill(Xf(RoundRect(RX - 3, Y - 26 - 3, RW + 6, 62, 20), {W / 2, Y + 5}, Ribbon), Faded(GInk, In));
    Pen.Fill(Xf(RoundRect(RX, Y - 26, RW, 56, 18), {W / 2, Y + 5}, Ribbon), Faded(GOrange, In));
    const FString Head = Guide->MissionKicker.IsEmpty() ? Guide->MissionTitle.ToUpper() : Guide->MissionKicker + TEXT("  ·  ") + Guide->MissionTitle.ToUpper();
    Pen.Centered(Head, W / 2, Y - 14, 1.2f * FMath::Max(Ribbon, .01f), Faded(FLinearColor::White, In));
    float RowY = Y + 58;
    for (int32 I = 0; I < Body.Num(); ++I, RowY += 32)
        Pen.Centered(Body[I], W / 2, RowY, .98f, Faded(GInk, Clamp01((T - .45f - .15f * I) / .25f)));
    if (StepCount)
    {
        RowY += 16;
        Pen.Text(TEXT("CÓMO LLEGAR"), X + 60, RowY, .72f, Faded(GOrange, Clamp01((T - .7f) / .2f)));
        RowY += 30;
        for (int32 I = 0; I < StepCount; ++I, RowY += 34)
        {
            const float RowIn = Clamp01((T - .8f - .12f * I) / .25f);
            const float Dx = 20 * (1.0f - EaseOutQuart((T - .8f - .12f * I) / .35f));
            Pen.Fill(Circle({X + 74 + Dx, RowY + 12}, 13, 20), Faded(GInk, RowIn));
            Pen.Centered(FString::FromInt(I + 1), X + 74 + Dx, RowY + 2, .72f, Faded(FLinearColor::White, RowIn));
            Pen.Text(Guide->Steps[I].Title, X + 100 + Dx, RowY + 1, .85f, Faded(GInk, RowIn));
        }
    }
    GuideContinueChip(Pen, TEXT("ESPACIO / CLIC  ·  ¡A TRABAJAR!"), W / 2, Y + CH - 58, T, Clamp01((T - 1.1f) / .3f));
    return true;
}

void AFactoryDemoHUD::DrawGuide(float S, float W, float H)
{
    const AFactoryGuide* Guide = AFactoryGuide::Find(GetWorld());
    const FFactoryGuideStep* Step = Guide ? Guide->GetStep() : nullptr;
    if (!Step) return;
    const float Now = GetWorld()->GetRealTimeSeconds(), T = Now - Guide->GetShownAt();
    const float DoneT = Now - Guide->GetStepDoneAt();
    const bool bDone = DoneT >= 0.0f && DoneT < 1.4f && Guide->GetStepDoneAt() >= Guide->GetShownAt();
    FPen Pen{this, Canvas, S, GEngine->GetMediumFont(), GEngine->GetLargeFont()};
    const auto* Mission = UFactoryMissionSubsystem::Get(this);
    const bool bProgress = Step->Goal == EFactoryGuideGoal::Deliver && Mission;

    // Objective card, right of the events sign: it drops in with each new step and leaves with a tick.
    const float CW = 470, CH = bProgress ? 118 : 92, X = 112, Y = 82;   // debajo del dinero, al lado del cartel de eventos
    const float K = bDone ? 1.0f - Clamp01((DoneT - 1.1f) / .3f) : EaseOutBack(T / .4f);
    const FVector2D Pivot(X, Y);
    Pen.Fill(Xf(RoundRect(X + 5, Y + 6, CW, CH, 18), Pivot, K), Faded(GInk, .3f));
    Pen.Fill(Xf(RoundRect(X - 3, Y - 3, CW + 6, CH + 6, 21), Pivot, K), GInk);
    Pen.Fill(Xf(RoundRect(X, Y, CW, CH, 18), Pivot, K), bDone ? Hex(0xE3FBEF) : GCream);
    const float In = Clamp01((T - .15f) / .2f) * Clamp01(K);
    const FString Kicker = FString::Printf(TEXT("%s  ·  PASO %d DE %d"), *Guide->MissionKicker, Guide->GetStepIndex() + 1, Guide->Steps.Num());
    Pen.Text(Kicker, X + 64, Y + 12, .66f, Faded(bDone ? GGreen : GOrange, In));
    Pen.Text(Step->Title, X + 64, Y + 32, .98f, Faded(GInk, In));
    Pen.Text(Step->Hint, X + 64, Y + 60, .72f, Faded(GMuted, In));
    // Badge on the left: a pulsing arrow while pending, a green tick when done.
    const FVector2D B(X + 34, Y + 44);
    if (bDone)
    {
        const float Pop = EaseOutBack(DoneT / .35f, 3.0f);
        Pen.Fill(Circle(B, 22 * Pop), Faded(GInk, In));
        Pen.Fill(Circle(B, 19 * Pop), Faded(GGreen, In));
        Pen.Fill(Xf(Quad({B.X - 11, B.Y - 1}, {B.X - 6, B.Y - 6}, {B.X - 1, B.Y}, {B.X - 5, B.Y + 5}), B, Pop), Faded(FLinearColor::White, In));
        Pen.Fill(Xf(Quad({B.X - 5, B.Y + 5}, {B.X + 10, B.Y - 11}, {B.X + 15, B.Y - 6}, {B.X - 1, B.Y + 10}), B, Pop), Faded(FLinearColor::White, In));
    }
    else
    {
        const float Pulse = 1.0f + .08f * FMath::Sin(Now * 5.0f);
        Pen.Fill(Circle(B, 22 * Pulse), Faded(GInk, In));
        Pen.Fill(Circle(B, 19 * Pulse), Faded(GOrange, In));
        const float Bob = 3 * FMath::Sin(Now * 5.0f);
        Pen.Fill(Quad({B.X - 4, B.Y - 12 + Bob}, {B.X + 4, B.Y - 12 + Bob}, {B.X + 4, B.Y + Bob}, {B.X - 4, B.Y + Bob}), Faded(FLinearColor::White, In));
        Pen.Fill({{B.X - 10, B.Y - 1 + Bob}, {B.X + 10, B.Y - 1 + Bob}, {B.X, B.Y + 11 + Bob}}, Faded(FLinearColor::White, In));
    }
    if (bProgress)
    {
        const float Fraction = Mission->Goal > 0 ? Clamp01(float(Mission->Delivered) / Mission->Goal) : 0.0f;
        Pen.Fill(RoundRect(X + 64, Y + 88, CW - 150, 16, 8), Faded(GInk, .15f * In));
        if (Fraction > 0) Pen.Fill(RoundRect(X + 64, Y + 88, FMath::Max((CW - 150) * Fraction, 16.0f), 16, 8), Faded(GGreen, In));
        Pen.Text(FString::Printf(TEXT("%d / %d"), FMath::Min(Mission->Delivered, Mission->Goal), Mission->Goal), X + CW - 76, Y + 85, .78f, Faded(GInk, In));
    }

    // The 3D arrow's target out of view: an orange arrow on the screen edge pointing at it, with the distance.
    FVector Point;
    APawn* Pawn = PlayerOwner ? PlayerOwner->GetPawn() : nullptr;
    if (!Guide->GetArrowPoint(Point) || !PlayerOwner) return;
    FVector2D Screen;
    const bool bFront = PlayerOwner->ProjectWorldLocationToScreen(Point, Screen);
    FVector2D P = Screen / S;
    const float Margin = 70;
    if (bFront && P.X > Margin && P.X < W - Margin && P.Y > Margin + 60 && P.Y < H - Margin - 44) return;
    const FVector2D Centre(W / 2, H / 2);
    FVector2D Dir = bFront ? P - Centre : Centre - P;
    if (Dir.IsNearlyZero()) Dir = FVector2D(0, -1);
    Dir.Normalize();
    // Where the line from the centre towards the target meets the margin box.
    const float HalfW = W / 2 - Margin, HalfH = H / 2 - Margin - 30;
    const float Reach = FMath::Min(FMath::Abs(Dir.X) > KINDA_SMALL_NUMBER ? HalfW / FMath::Abs(Dir.X) : BIG_NUMBER,
                                   FMath::Abs(Dir.Y) > KINDA_SMALL_NUMBER ? HalfH / FMath::Abs(Dir.Y) : BIG_NUMBER);
    const FVector2D At = Centre + Dir * Reach;
    const float Angle = FMath::RadiansToDegrees(FMath::Atan2(Dir.Y, Dir.X));
    const float Nudge = 6 * FMath::Sin(Now * 6.0f);
    const FVector2D Tip = At + Dir * Nudge;
    const FPts Chevron = {{26, 0}, {-14, -22}, {-6, 0}, {-14, 22}};
    Pen.Fill(Xf(Xf(Chevron, FVector2D::ZeroVector, 1.25f), FVector2D::ZeroVector, 1.0f, Tip, Angle), GInk);
    Pen.Fill(Xf(Chevron, FVector2D::ZeroVector, 1.0f, Tip, Angle), GOrange);
    if (Pawn)
    {
        const FString Distance = FString::Printf(TEXT("%d m"), FMath::RoundToInt(FVector::Dist2D(Pawn->GetActorLocation(), Point) / 100.0f));
        const FVector2D L = Tip - Dir * 52;
        const float LW = Pen.Width(Distance, .72f) + 20;
        Pen.Fill(RoundRect(L.X - LW / 2, L.Y - 13, LW, 26, 13), GInk);
        Pen.Centered(Distance, L.X, L.Y - 10, .72f, FLinearColor::White);
    }
}

void AFactoryDemoHUD::DrawMoney(float S, float W, float H)
{
    const UFactoryEconomySubsystem* Economy = UFactoryEconomySubsystem::Get(this);
    if (!Economy) return;
    FPen Pen{this, Canvas, S, GEngine->GetMediumFont(), GEngine->GetLargeFont()};
    const float Now = GetWorld()->GetRealTimeSeconds();
    const TArray<FFactoryMoneyChange>& Changes = Economy->GetChanges();
    const FFactoryMoneyChange* Last = Changes.IsEmpty() ? nullptr : &Changes.Last();
    const float Since = Last ? Now - Last->At : 100.0f;
    // The pill jumps a little when the money changes.
    const float Jump = Since < .45f ? 1.0f + .12f * (1.0f - EaseOutBack(Since / .45f, 3.0f)) : 1.0f;
    const FString Amount = UFactoryEconomySubsystem::Format(Economy->GetMoney());
    const float X = 24, Y = 18, PH = 46, PW = Pen.Width(Amount, 1.15f) + 80;
    const FVector2D Pivot(X + 23, Y + PH / 2);
    Pen.Fill(Xf(RoundRect(X + 4, Y + 5, PW, PH, 23), Pivot, Jump), Faded(GInk, .3f));
    Pen.Fill(Xf(RoundRect(X - 3, Y - 3, PW + 6, PH + 6, 26), Pivot, Jump), GInk);
    Pen.Fill(Xf(RoundRect(X, Y, PW, PH, 23), Pivot, Jump), GCream);
    // Coin: gold disc with a "$".
    const FVector2D Coin(X + 23, Y + PH / 2);
    Pen.Fill(Xf(Circle(Coin, 17, 28), Pivot, Jump), GInk);
    Pen.Fill(Xf(Circle(Coin, 14, 28), Pivot, Jump), Hex(0xFFC928));
    Pen.Centered(TEXT("$"), Coin.X, Coin.Y - 11, .82f * Jump, GInk);
    const bool bFlash = Since < .8f && Last;
    Pen.Text(Amount, X + 48, Y + 9, 1.15f * Jump, bFlash ? (Last->Amount > 0 ? Hex(0x1E9E5A) : Hex(0xE5484D)) : GInk);
    // Sound buttons, always there: round stickers, music (a note) and sounds (a speaker), crossed out when silenced;
    // they grow under the mouse.
    float MouseX = 0, MouseY = 0;
    const bool bMouse = PlayerOwner && PlayerOwner->GetMousePosition(MouseX, MouseY);
    {
        const FVector2D NC(X + PW + 34, Y + PH / 2);
        const bool bNoteOver = bMouse && FVector2D::Distance(FVector2D(MouseX, MouseY) / S, NC) < 24;
        const float NR = bNoteOver ? 24 : 22;
        Pen.Fill(Circle(NC + FVector2D(3, 4), NR + 3), Faded(GInk, .3f));
        Pen.Fill(Circle(NC, NR + 3), GInk);
        Pen.Fill(Circle(NC, NR), bMusicMuted ? Hex(0xE5484D) : GCream);
        const FLinearColor NoteInk = bMusicMuted ? FLinearColor::White : GInk;
        // Two eighth notes joined by a beam.
        Pen.Fill(Circle(NC + FVector2D(-7, 8), 4.5f, 16), NoteInk);
        Pen.Fill(Circle(NC + FVector2D(7, 5), 4.5f, 16), NoteInk);
        Pen.Fill(Quad(NC + FVector2D(-4, 8), NC + FVector2D(-2, 8), NC + FVector2D(-2, -10), NC + FVector2D(-4, -10)), NoteInk);
        Pen.Fill(Quad(NC + FVector2D(10, 5), NC + FVector2D(12, 5), NC + FVector2D(12, -13), NC + FVector2D(10, -13)), NoteInk);
        Pen.Fill(Quad(NC + FVector2D(-4, -10), NC + FVector2D(12, -13), NC + FVector2D(12, -8), NC + FVector2D(-4, -5)), NoteInk);
        if (bMusicMuted)
            Pen.Fill(Quad(NC + FVector2D(-13, -14), NC + FVector2D(-9, -16), NC + FVector2D(13, 14), NC + FVector2D(9, 16)), NoteInk);
        MusicCorner = FBox2D((NC - FVector2D(NR + 3, NR + 3)) * S, (NC + FVector2D(NR + 3, NR + 3)) * S);
    }
    const FVector2D MC(X + PW + 90, Y + PH / 2);
    const bool bOver = bMouse && FVector2D::Distance(FVector2D(MouseX, MouseY) / S, MC) < 24;
    const float MR = bOver ? 24 : 22;
    Pen.Fill(Circle(MC + FVector2D(3, 4), MR + 3), Faded(GInk, .3f));
    Pen.Fill(Circle(MC, MR + 3), GInk);
    Pen.Fill(Circle(MC, MR), bSoundsMuted ? Hex(0xE5484D) : GCream);
    const FLinearColor Icon = bSoundsMuted ? FLinearColor::White : GInk;
    Pen.Fill(Quad(MC + FVector2D(-11, -4), MC + FVector2D(-5, -4), MC + FVector2D(-5, 4), MC + FVector2D(-11, 4)), Icon);
    Pen.Fill({MC + FVector2D(-6, -4), MC + FVector2D(3, -11), MC + FVector2D(3, 11), MC + FVector2D(-6, 4)}, Icon);
    if (bSoundsMuted)
        Pen.Fill(Quad(MC + FVector2D(-13, -14), MC + FVector2D(-9, -16), MC + FVector2D(13, 14), MC + FVector2D(9, 16)), Icon);
    else
        for (int32 Wave = 0; Wave < 2; ++Wave)
        {
            const float R = 7 + 5 * Wave;
            for (int32 I = 0; I < 5; ++I)
            {
                const float A0 = FMath::DegreesToRadians(-40 + 16 * I), A1 = FMath::DegreesToRadians(-40 + 16 * (I + 1));
                const FVector2D O = MC + FVector2D(4, 0);
                Pen.Fill(Quad(O + FVector2D(FMath::Cos(A0), FMath::Sin(A0)) * R, O + FVector2D(FMath::Cos(A1), FMath::Sin(A1)) * R,
                              O + FVector2D(FMath::Cos(A1), FMath::Sin(A1)) * (R + 2.2f), O + FVector2D(FMath::Cos(A0), FMath::Sin(A0)) * (R + 2.2f)), Icon);
            }
        }
    MuteCorner = FBox2D((MC - FVector2D(MR + 3, MR + 3)) * S, (MC + FVector2D(MR + 3, MR + 3)) * S);
    // First person button, next to mute: an eye; orange while the camera is at the character's eyes.
    {
        const APawn* Pawn = PlayerOwner ? PlayerOwner->GetPawn() : nullptr;
        const auto* Camera = Pawn ? Pawn->FindComponentByClass<UFactoryCameraComponent>() : nullptr;
        const bool bOn = Camera && Camera->IsFirstPerson();
        const FVector2D EC(MC.X + 56, MC.Y);
        const bool bEyeOver = bMouse && FVector2D::Distance(FVector2D(MouseX, MouseY) / S, EC) < 24;
        const float ER = bEyeOver ? 24 : 22;
        Pen.Fill(Circle(EC + FVector2D(3, 4), ER + 3), Faded(GInk, .3f));
        Pen.Fill(Circle(EC, ER + 3), GInk);
        Pen.Fill(Circle(EC, ER), bOn ? GOrange : GCream);
        const FLinearColor EyeInk = bOn ? FLinearColor::White : GInk;
        // Almond: two arcs; iris and pupil in the middle.
        TArray<FVector2D> Almond;
        for (int32 I = 0; I <= 12; ++I)
        {
            const float A = PI * I / 12.0f;
            Almond.Add(EC + FVector2D(-13 * FMath::Cos(A), -8 * FMath::Sin(A)));
        }
        for (int32 I = 1; I < 12; ++I)
        {
            const float A = PI * I / 12.0f;
            Almond.Add(EC + FVector2D(13 * FMath::Cos(A), 8 * FMath::Sin(A)));
        }
        Pen.Fill(Almond, EyeInk);
        Pen.Fill(Circle(EC, 6, 20), bOn ? GOrange : GCream);
        Pen.Fill(Circle(EC, 3, 16), EyeInk);
        Pen.Centered(bOn ? TEXT("1ª") : TEXT("1ª"), EC.X + 15, EC.Y + 9, .5f, EyeInk);
        FirstPersonCorner = FBox2D((EC - FVector2D(ER + 3, ER + 3)) * S, (EC + FVector2D(ER + 3, ER + 3)) * S);
        if (bOn)   // punto de mira
        {
            Pen.Fill(Circle(FVector2D(W / 2, H / 2), 4.5f, 16), Faded(GInk, .6f));
            Pen.Fill(Circle(FVector2D(W / 2, H / 2), 2.5f, 16), FLinearColor::White);
        }
    }
    // Recent changes float up and fade next to the pill.
    for (const FFactoryMoneyChange& Change : Changes)
    {
        const float T = Now - Change.At;
        if (T < 0.0f || T > 2.2f) continue;
        const FString Text = (Change.Amount > 0 ? TEXT("+") : TEXT("")) + UFactoryEconomySubsystem::Format(Change.Amount);
        const float Alpha = T < .2f ? T / .2f : 1.0f - Clamp01((T - 1.4f) / .8f);
        const float PX = X + PW + 186, PY = Y + 10 - 26 * EaseOutQuart(T / 2.2f);
        const float TW = Pen.Width(Text, .9f) + 20;
        Pen.Fill(RoundRect(PX, PY - 2, TW, 30, 15), Faded(Change.Amount > 0 ? GGreen : Hex(0xE5484D), Alpha));
        Pen.Text(Text, PX + 10, PY + 3, .9f, Faded(FLinearColor::White, Alpha));
    }
}

void AFactoryDemoHUD::DrawInteraction(float S, float W, float H)
{
    const APawn* Pawn = PlayerOwner ? PlayerOwner->GetPawn() : nullptr;
    if (!Pawn) return;
    const auto* Camera = Pawn->FindComponentByClass<UFactoryCameraComponent>();
    const bool bFirstPerson = Camera && Camera->IsFirstPerson();
    FString Hint;
    if (bFirstPerson)
    {
        // The prompts the actors show in the world when the character is near: the nearest one.
        double Best = FMath::Square(450.0);
        for (TObjectIterator<UTextRenderComponent> It; It; ++It)
        {
            const UTextRenderComponent* Prompt = *It;
            if (Prompt->GetWorld() != GetWorld() || Prompt->bHiddenInGame || !Prompt->IsVisible() || !Prompt->GetName().Contains(TEXT("Prompt"))) continue;
            const double Distance = FVector::DistSquared(Prompt->GetComponentLocation(), Pawn->GetActorLocation());
            if (Distance < Best && !Prompt->Text.IsEmpty()) { Best = Distance; Hint = Prompt->Text.ToString(); }
        }
    }
    if (Hint.IsEmpty())
    {
        // A pile to pick up (only its ring shows in the world), or something to load from the inventory.
        const auto* Gathering = Pawn->FindComponentByClass<UFactoryGatheringComponent>();
        auto* Demo = Pawn->FindComponentByClass<UFactoryDemoComponent>();
        const auto* Inventory = Demo ? Demo->Inventory() : nullptr;
        if (Demo && !Demo->bBuilding) Demo->RefreshFocus();
        const AFactoryBuilding* Building = Demo ? Demo->FocusedBuilding.Get() : nullptr;
        const AFactoryResourcePile* Pile = Gathering ? Gathering->FocusedPile.Get() : nullptr;
        const bool bPileFirst = Pile && (!Building || FVector::DistSquared2D(Pawn->GetActorLocation(), Pile->GetActorLocation())
            < FVector::DistSquared2D(Pawn->GetActorLocation(), Building->GetActorLocation()));
        if (bPileFirst && Pile->Resource) Hint = FString::Printf(TEXT("[E] JUNTAR %s"), *Pile->Resource->DisplayName.ToString().ToUpper());
        else if (Building && Inventory && Demo->Factory)
            for (const UFactoryResourceDefinition* Item : Demo->Factory->Resources)
                if (Item && Inventory->GetQuantity(Item->ItemId) > 0 && Building->CanAccept(Item->ItemId))
                {
                    const bool bBelt = Building->Definition && Building->Definition->Kind == EFactoryBuildingKind::Belt;
                    Hint = FString::Printf(TEXT("[E] CARGAR %s %s"), *Item->DisplayName.ToString().ToUpper(), bBelt ? TEXT("EN LA CINTA") : TEXT("EN LA MÁQUINA"));
                    break;
                }
    }
    if (Hint.IsEmpty()) return;
    Hint.ReplaceInline(TEXT("<br>"), TEXT("  "));
    Hint.ReplaceInline(TEXT("\n"), TEXT("  "));
    // First person: under the crosshair; the isometric view: over the hints bar at the bottom.
    FPen Pen{this, Canvas, S, GEngine->GetMediumFont(), GEngine->GetLargeFont()};
    const float TW = Pen.Width(Hint, .9f) + 34, CX = W / 2, CY = bFirstPerson ? H / 2 + 46 : H - 92;
    Pen.Fill(RoundRect(CX - TW / 2 + 3, CY + 4, TW, 34, 17), Faded(GInk, .3f));
    Pen.Fill(RoundRect(CX - TW / 2 - 3, CY - 3, TW + 6, 40, 20), GInk);
    Pen.Fill(RoundRect(CX - TW / 2, CY, TW, 34, 17), GCream);
    Pen.Centered(Hint, CX, CY + 6, .9f, GInk);
}

void AFactoryDemoHUD::DrawNpcSpeech(float S, float W, float H)
{
    if (!PlayerOwner) return;
    FPen Pen{this, Canvas, S, GEngine->GetMediumFont(), GEngine->GetLargeFont()};
    const float Now = GetWorld()->GetRealTimeSeconds();
    for (TActorIterator<AFactoryNpc> It(GetWorld()); It; ++It)
    {
        const AFactoryNpc* Npc = *It;
        if (!Npc->IsTalking() || Npc->GetLine().IsEmpty()) continue;
        FVector2D Screen;
        if (!PlayerOwner->ProjectWorldLocationToScreen(Npc->GetActorLocation() + FVector(0, 0, Npc->SpeechHeight), Screen)) continue;
        const FVector2D Tip = Screen / S;
        const float T = Now - Npc->GetLineShownAt();
        // Pops in with each line; shrinks away when the player leaves.
        const float K = Npc->IsNear() ? EaseOutBack(T / .35f) : 1.0f - Clamp01((Now - Npc->GetLeftAt()) / .3f);
        if (K <= .01f) continue;
        const FString Line = Npc->GetLine();
        // Typewriter: the line appears letter by letter.
        const int32 Shown = FMath::Clamp(FMath::FloorToInt((T - .2f) * 28.0f), 0, Line.Len());
        const float TW = FMath::Max(Pen.Width(Line, 1.05f), 90.0f);
        const float BW = TW + 44, BH = 62, BX = FMath::Clamp(Tip.X - BW / 2, 12.0f, W - BW - 12), BY = Tip.Y - BH - 22;
        const FVector2D Pivot(Tip.X, Tip.Y);
        Pen.Fill(Xf(RoundRect(BX + 5, BY + 6, BW, BH, 22), Pivot, K), Faded(GInk, .3f * K));
        Pen.Fill(Xf(RoundRect(BX - 3, BY - 3, BW + 6, BH + 6, 25), Pivot, K), GInk);
        Pen.Fill(Xf({{Tip.X - 13, BY + BH - 2}, {Tip.X + 13, BY + BH - 2}, {Tip.X, Tip.Y + 4}}, Pivot, K), GInk);
        Pen.Fill(Xf(RoundRect(BX, BY, BW, BH, 22), Pivot, K), GCream);
        Pen.Fill(Xf({{Tip.X - 9, BY + BH - 3}, {Tip.X + 9, BY + BH - 3}, {Tip.X, Tip.Y - 2}}, Pivot, K), GCream);
        const float In = Clamp01((T - .15f) / .15f) * K;
        // Name tag on the top left corner.
        const float NW = Pen.Width(Npc->DisplayName.ToUpper(), .62f) + 22;
        Pen.Fill(Xf(RoundRect(BX + 14, BY - 14, NW, 24, 12), Pivot, K), Faded(GOrange, In));
        Pen.Text(Npc->DisplayName.ToUpper(), BX + 25, BY - 11, .62f, Faded(FLinearColor::White, In));
        Pen.Text(Line.Left(Shown), BX + 22, BY + 17, 1.05f, Faded(GInk, In));
    }
}

FString AFactoryDemoHUD::GuideElevatorStop() const
{
    const AFactoryGuide* Guide = AFactoryGuide::Find(GetWorld());
    const FFactoryGuideStep* Step = Guide ? Guide->GetStep() : nullptr;
    return Step ? Step->ElevatorStop : FString();
}
