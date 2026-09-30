// Info panel (key I), "Pegatina Pop" look (chosen on 28/09 among three; the other two are kept in
// Saved/Respaldos/2026-09-28_interfaz_3_estilos): a cartoon sticker card with the portrait, the welcome, the
// objective with its progress and the mute option. Drawn with the HUD canvas only; every motion comes from
// the time since the panel appeared (T).
#include "FactoryDemo.h"
#include "EngineUtils.h"
#include "FactoryDispatchBelt.h"
#include "FactoryEconomy.h"
#include "FactoryGathering.h"
#include "FactoryGateBarrier.h"
#include "FactoryMission.h"
#include "FactoryRollDoor.h"
#include "FactoryStaff.h"
#include "FactoryVehiclePath.h"
#include "CanvasItem.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GlobalRenderResources.h"

#include "FactoryHudDraw.h"

using namespace FactoryHudDraw;

namespace
{
    /** One thing on the events list. */
    struct FGameEvent
    {
        FString Title, Hint;
        int32 Kind = 0;   // 0 truck, 1 belt
    };

    /** The panel's content, the same in every look. */
    struct FInfo
    {
        UTexture2D* Portrait = nullptr;
        int32 Done = 0, Goal = 20;
        bool bComplete = false, bMuted = false;
        float SinceDelivery = 100.0f;   // seconds since the count last went up
        float SinceMute = 100.0f;
        FVector2D Mouse = FVector2D(-1, -1);   // design units
    };
    const TCHAR* Greeting = TEXT("¡Hola! Soy TecJunior.");
    const TCHAR* Lines[] = {TEXT("Me toca despachar los pedidos del depósito:"), TEXT("sacá las cajas de las cintas de despacho"),
                            TEXT("y cargalas en los camiones.")};

    /** Letters shown after Seconds at Speed per second, across the greeting and the lines. */
    FString Typed(const FString& Value, float& Budget)
    {
        const int32 Count = FMath::Clamp(FMath::FloorToInt(Budget), 0, Value.Len());
        Budget -= Value.Len();
        return Value.Left(Count);
    }
}

void AFactoryDemoHUD::DrawCharacterPanel(float S, float W, float H)
{
    if (!Portrait) Portrait = LoadObject<UTexture2D>(nullptr, TEXT("/Game/FactoryCtyco/UI/T_RetratoTecJunior.T_RetratoTecJunior"));
    const float Now = GetWorld()->GetRealTimeSeconds();
    const float T = Now - InfoShownAt;
    FPen Pen{this, Canvas, S, GEngine->GetMediumFont(), GEngine->GetLargeFont()};
    FInfo Info;
    Info.Portrait = Portrait;
    if (const auto* Mission = GetWorld()->GetSubsystem<UFactoryMissionSubsystem>())
    {
        Info.Done = FMath::Min(Mission->Delivered, Mission->Goal);
        Info.Goal = Mission->Goal;
        Info.bComplete = Mission->bCompleted;
        if (SeenDelivered >= 0 && Mission->Delivered != SeenDelivered) DeliveredAt = Now;
        SeenDelivered = Mission->Delivered;
    }
    Info.SinceDelivery = Now - DeliveredAt;
    Info.bMuted = bMuted;
    Info.SinceMute = Now - MutedAt;
    float MX = -1, MY = -1;
    if (PlayerOwner && PlayerOwner->GetMousePosition(MX, MY)) Info.Mouse = FVector2D(MX, MY) / S;

    MuteButton = FBox2D(ForceInit);
    auto SetButton = [&](float X, float Y, float BW, float BH) { MuteButton = FBox2D(FVector2D(X, Y) * S, FVector2D(X + BW, Y + BH) * S); };
    auto Hover = [&](float X, float Y, float BW, float BH) { return Info.Mouse.X >= X && Info.Mouse.X <= X + BW && Info.Mouse.Y >= Y && Info.Mouse.Y <= Y + BH; };

    {
        const FLinearColor Cream = Hex(0xFFF4E0), Orange = Hex(0xFF8A1F), Blue = Hex(0x2F6FD6), Ink = Hex(0x2B2340),
            Green = Hex(0x3DD68C), Card = Hex(0xC89B61), Red = Hex(0xE5484D), White = FLinearColor::White;
        Pen.Rect(0, 0, W, H, FLinearColor(0, 0, 0, .28f * Clamp01(T / .2f)));
        const float CW = 680, CH = 390, CX = W / 2, CY = H / 2 - 10, L = CX - CW / 2, Top = CY - CH / 2;
        const float K = EaseOutBack(T / .35f), Drop = -40.0f * (1.0f - EaseOutQuart(T / .35f));
        const FVector2D Pivot(CX, CY), Off(0, Drop);
        // One element entering: pops from 0.8 about its own centre after its delay (stagger 60 ms).
        auto Pop = [&](int32 Index) { return FMath::Lerp(0.8f, 1.0f, EaseOutBack((T - .12f - .06f * Index) / .25f)); };
        auto Seen = [&](int32 Index) { return Clamp01((T - .12f - .06f * Index) / .08f); };
        auto Card2 = [&](const FPts& P, FVector2D Own, float PopScale) { return Xf(Xf(P, Own, PopScale), Pivot, K, Off); };

        // Card: hard shadow, ink border, cream body.
        Pen.Fill(Xf(RoundRect(L + 8, Top + 8, CW, CH, 26), Pivot, K, Off), Faded(Ink, .35f));
        Pen.Fill(Xf(RoundRect(L - 4, Top - 4, CW + 8, CH + 8, 30), Pivot, K, Off), Ink);
        Pen.Fill(Xf(RoundRect(L, Top, CW, CH, 26), Pivot, K, Off), Cream);

        // Tabs on the top edge, right: the page shown is orange, the other cream; hover lifts a little.
        const TCHAR* TabNames[2] = {TEXT("INICIO"), TEXT("CONTRATAR")};
        for (int32 Tab = 0; Tab < 2; ++Tab)
        {
            const float TW = 150, TH = 40, TX = L + CW - 340 + Tab * (TW + 14), TY = Top - 22;
            const bool bOn = InfoTab == Tab, bHover = !bOn && Hover(TX, TY, TW, TH);
            const float Lift = bHover ? -3 : 0;
            const FVector2D TC(TX + TW / 2, TY + TH / 2);
            const float TP = Pop(1);
            Pen.Fill(Card2(RoundRect(TX + 4, TY + 5 + Lift, TW, TH, 20), TC, TP), Faded(Ink, .35f * Seen(1)));
            Pen.Fill(Card2(RoundRect(TX - 3, TY - 3 + Lift, TW + 6, TH + 6, 23), TC, TP), Faded(Ink, Seen(1)));
            Pen.Fill(Card2(RoundRect(TX, TY + Lift, TW, TH, 20), TC, TP), Faded(bOn ? Orange : Cream, Seen(1)));
            const FVector2D At = Xf({FVector2D(TC.X, TY + 10 + Lift)}, Pivot, K, Off)[0];
            Pen.Centered(TabNames[Tab], At.X, At.Y, .9f * K * TP, Faded(bOn ? White : Ink, Seen(1)));
            if (!bOn) TabButtons[Tab] = FBox2D(FVector2D(TX, TY) * S, FVector2D(TX + TW, TY + TH) * S);
        }

        // Portrait sticker: sticks out of the top left corner, bobs and sways a little.
        const float Bob = 3.0f * FMath::Sin(T * 2.2f), Sway = 2.0f * FMath::Sin(T * 1.6f + 1.0f);
        const FVector2D PC(L + 118, Top + 70 + Bob);
        const float PP = Pop(0), R = 92;
        Pen.Fill(Card2(Circle(PC + FVector2D(5, 6), R + 8), PC, PP), Faded(Ink, .35f * Seen(0)));
        Pen.Fill(Card2(Circle(PC, R + 8), PC, PP), Faded(Ink, Seen(0)));
        Pen.Fill(Card2(Circle(PC, R + 4), PC, PP), Faded(Orange, Seen(0)));
        if (Info.Portrait)
        {
            const FPts Disc = Circle(PC, R, 48);
            Pen.Fill(Card2(Disc, PC, PP), Faded(Hex(0xFFE2B8), Seen(0)));
            // UVs from the unrotated disc, positions rotated: the picture sways with the sticker.
            const FPts Placed = Card2(Xf(Disc, PC, 1.0f, FVector2D::ZeroVector, Sway), PC, PP);
            const FPts Base = Card2(Disc, PC, PP);
            FBox2D Box(ForceInit);
            for (const FVector2D& V : Base) Box += V;
            // Map the texture through the unrotated disc, then draw the rotated positions with the same UVs.
            TArray<FCanvasUVTri> Tris;
            FVector2D Ctr = FVector2D::ZeroVector, CtrUV = FVector2D::ZeroVector;
            for (int32 I = 0; I < Placed.Num(); ++I) { Ctr += Placed[I]; CtrUV += (Base[I] - Box.Min) / (Box.Max - Box.Min); }
            Ctr /= Placed.Num(); CtrUV /= Placed.Num();
            for (int32 I = 0; I < Placed.Num(); ++I)
            {
                const int32 J = (I + 1) % Placed.Num();
                FCanvasUVTri Tri;
                Tri.V0_Pos = Ctr * S; Tri.V1_Pos = Placed[I] * S; Tri.V2_Pos = Placed[J] * S;
                Tri.V0_UV = CtrUV; Tri.V1_UV = (Base[I] - Box.Min) / (Box.Max - Box.Min); Tri.V2_UV = (Base[J] - Box.Min) / (Box.Max - Box.Min);
                Tri.V0_Color = Tri.V1_Color = Tri.V2_Color = FLinearColor(1, 1, 1, Seen(0));
                Tris.Add(Tri);
            }
            FCanvasTriangleItem Item(Tris, Info.Portrait->GetResource() ? Info.Portrait->GetResource() : GWhiteTexture);
            Item.BlendMode = SE_BLEND_Translucent;
            Canvas->DrawItem(Item);
        }
        // Name tag under the sticker.
        {
            const FVector2D NC(L + 118, Top + 186);
            const float NP = Pop(1);
            Pen.Fill(Card2(RoundRect(NC.X - 84 + 4, NC.Y - 18 + 4, 168, 36, 18), NC, NP), Faded(Ink, .35f * Seen(1)));
            Pen.Fill(Card2(RoundRect(NC.X - 86, NC.Y - 20, 172, 40, 20), NC, NP), Faded(Ink, Seen(1)));
            Pen.Fill(Card2(RoundRect(NC.X - 84, NC.Y - 18, 168, 36, 18), NC, NP), Faded(Orange, Seen(1)));
            const FVector2D TextAt = Xf({NC}, Pivot, K, Off)[0];
            Pen.Centered(TEXT("TECJUNIOR"), TextAt.X, TextAt.Y - 11 * K, 1.0f * K * NP, Faded(White, Seen(1)));
            Pen.Centered(TEXT("Técnico de despacho"), TextAt.X, TextAt.Y + 26 * K, .78f * K, Faded(Ink, Seen(1)));
        }
        if (InfoTab == 1)
        {
            // Hire page: a ribbon with the title and one card per job (for now, the barrier attendant).
            const float TT = Now - FMath::Max(InfoShownAt, InfoTabAt);
            const float In = Clamp01((T - .2f) / .15f) * Clamp01(TT / .15f);
            const float RX = L + 250, RW = CW - 274, RY = Top + 34;
            const float RK = EaseOutBack(TT / .3f);
            const FVector2D RC(RX + RW / 2, RY + 26);
            Pen.Fill(Card2(RoundRect(RX + 4, RY + 5, RW, 52, 16), RC, RK), Faded(Ink, .3f * In));
            Pen.Fill(Card2(RoundRect(RX - 3, RY - 3, RW + 6, 58, 18), RC, RK), Faded(Ink, In));
            Pen.Fill(Card2(RoundRect(RX, RY, RW, 52, 16), RC, RK), Faded(Blue, In));
            const FVector2D At = Xf({FVector2D(RX + 18, RY + 8)}, Pivot, K, Off)[0];
            Pen.Text(TEXT("CONTRATAR PERSONAL"), At.X, At.Y, 1.0f * K, Faded(White, In));
            Pen.Text(TEXT("Tu equipo trabaja mientras vos cargás."), At.X, At.Y + 24 * K, .72f * K, Faded(Hex(0xDCE8FF), In));
            if (K > .98f) HireButton = DrawHireCard(S, RX, RY + 78, RW, In, Info.Mouse);
            Pen.Centered(TEXT("I: cerrar"), CX, Top + CH - 34, .75f, Faded(Hex(0x8A7F98), Seen(5)));
            return;
        }
        // Speech bubble with a tail toward the portrait; the text types itself in (40 letters per second).
        {
            const float BX = L + 250, BY = Top + 26, BW = CW - 274, BH = 120;
            const FVector2D BC(BX + BW / 2, BY + BH / 2);
            const float BP = Pop(2);
            Pen.Fill(Card2(RoundRect(BX + 5, BY + 6, BW, BH, 20), BC, BP), Faded(Ink, .3f * Seen(2)));
            Pen.Fill(Card2(RoundRect(BX - 3, BY - 3, BW + 6, BH + 6, 22), BC, BP), Faded(Ink, Seen(2)));
            Pen.Fill(Card2(Quad({BX + 2, BY + 38}, {BX - 30, BY + 64}, {BX + 2, BY + 70}, {BX + 2, BY + 54}), BC, BP), Faded(Ink, Seen(2)));
            Pen.Fill(Card2(RoundRect(BX, BY, BW, BH, 20), BC, BP), Faded(White, Seen(2)));
            Pen.Fill(Card2(Quad({BX + 4, BY + 42}, {BX - 22, BY + 63}, {BX + 4, BY + 66}, {BX + 4, BY + 54}), BC, BP), Faded(White, Seen(2)));
            float Budget = FMath::Max(0.0f, (T - .35f) * 85.0f);   // letters per second
            const FVector2D At = Xf({FVector2D(BX + 18, BY + 12)}, Pivot, K, Off)[0];
            Pen.Text(Typed(Greeting, Budget), At.X, At.Y, 1.15f * K, Faded(Ink, Seen(2)));
            for (int32 I = 0; I < 3; ++I)
                Pen.Text(Typed(Lines[I], Budget), At.X, At.Y + (40 + I * 21) * K, .8f * K, Faded(Hex(0x5A4E6E), Seen(2)));
        }
        // Objective ribbon and 20 box cells.
        {
            const float OX = L + 250, OY = Top + 166, OW = CW - 274;
            const FVector2D OC(OX + OW / 2, OY + 23);
            const float OP = Pop(3);
            Pen.Fill(Card2(RoundRect(OX + 4, OY + 5, OW, 46, 14), OC, OP), Faded(Ink, .3f * Seen(3)));
            Pen.Fill(Card2(RoundRect(OX - 3, OY - 3, OW + 6, 52, 16), OC, OP), Faded(Ink, Seen(3)));
            Pen.Fill(Card2(RoundRect(OX, OY, OW, 46, 14), OC, OP), Faded(Info.bComplete ? Green : Orange, Seen(3)));
            const FVector2D At = Xf({FVector2D(OX + 16, OY + 11)}, Pivot, K, Off)[0];
            Pen.Text(Info.bComplete ? TEXT("¡OBJETIVO CUMPLIDO!") : TEXT("OBJETIVO: entregar 20 paquetes"), At.X, At.Y, .9f * K, Faded(White, Seen(3)));
            const float Jump = Info.SinceDelivery < .4f ? 1.0f + .4f * (1.0f - EaseOutBack(Info.SinceDelivery / .4f)) : 1.0f;
            const FString Count = FString::Printf(TEXT("%d/%d"), Info.Done, Info.Goal);
            const FVector2D CountAt = Xf({FVector2D(OX + OW - 16, OY + 9)}, Pivot, K, Off)[0];
            Pen.Text(Count, CountAt.X - Pen.Width(Count, 1.0f * K * Jump), CountAt.Y, 1.0f * K * Jump, Faded(Info.SinceDelivery < .4f ? Green : Ink, Seen(3)));
            const float Cell = 22, Gap = (OW - 20 * Cell) / 19;
            for (int32 I = 0; I < 20; ++I)
            {
                const float CXl = OX + I * (Cell + Gap), CYt = OY + 60;
                const FVector2D CC(CXl + Cell / 2, CYt + Cell / 2);
                float CP = FMath::Lerp(0.2f, 1.0f, EaseOutBack((T - .4f - .02f * I) / .2f));
                const bool bFull = I < Info.Done;
                FVector2D Squash(1, 1);
                if (bFull && I == Info.Done - 1 && Info.SinceDelivery < .3f)
                {
                    const float A = Info.SinceDelivery / .3f;   // squash & stretch of the newest cell
                    Squash = A < .4f ? FVector2D(1.3f, .7f) : A < .8f ? FVector2D(.9f, 1.1f) : FVector2D(1, 1);
                }
                auto CellPts = [&](float Grow) { FPts P = RoundRect(CXl - Grow, CYt - Grow, Cell + 2 * Grow, Cell + 2 * Grow, 5, 2);
                    for (FVector2D& V : P) V = CC + (V - CC) * Squash; return Card2(P, CC, CP); };
                const float CellSeen = Clamp01((T - .4f - .02f * I) / .06f);
                Pen.Fill(CellPts(2), Faded(Ink, CellSeen));
                Pen.Fill(CellPts(0), Faded(bFull ? Card : Cream, CellSeen));
                if (bFull) Pen.Fill(Card2(Quad({CXl + 9, CYt}, {CXl + 13, CYt}, {CXl + 13, CYt + Cell}, {CXl + 9, CYt + Cell}), CC, CP), Faded(Hex(0xE8C98F), CellSeen));
            }
        }
        // Mute button: blue pill with a hard shadow that "presses" under the mouse.
        {
            const float BX = L + 250, BY = Top + 272, BW = CW - 274, BH = 48;
            const bool bHover = Hover(BX, BY, BW, BH);
            const float Lift = bHover ? 3 : 6, HS = bHover ? 1.04f : 1.0f;
            const FVector2D BC(BX + BW / 2, BY + BH / 2);
            const float BP = Pop(4) * HS;
            Pen.Fill(Card2(RoundRect(BX + Lift, BY + Lift, BW, BH, 24), BC, BP), Faded(Ink, Seen(4)));
            Pen.Fill(Card2(RoundRect(BX - 3, BY - 3, BW + 6, BH + 6, 27), BC, BP), Faded(Ink, Seen(4)));
            Pen.Fill(Card2(RoundRect(BX, BY, BW, BH, 24), BC, BP), Faded(Info.bMuted ? Red : Blue, Seen(4)));
            const FVector2D At = Xf({FVector2D(BX + 22, BY + 13)}, Pivot, K, Off)[0];
            Pen.Text(TEXT("Silenciar juego"), At.X, At.Y, .95f * K * BP, Faded(White, Seen(4)));
            const FString State = Info.bMuted ? TEXT("SILENCIADO [M]") : TEXT("SONIDO: SÍ [M]");
            const FVector2D SAt = Xf({FVector2D(BX + BW - 22, BY + 15)}, Pivot, K, Off)[0];
            Pen.Text(State, SAt.X - Pen.Width(State, .8f * K * BP), SAt.Y, .8f * K * BP, Faded(White, Seen(4)));
            SetButton(BX, BY, BW, BH);
        }
        Pen.Centered(TEXT("I: cerrar"), CX, Top + CH - 34, .75f, Faded(Hex(0x8A7F98), Seen(5)));
    }
}

namespace
{
    /** What is going on that the player may want to act on. */
    TArray<FGameEvent> CollectEvents(const UWorld* World)
    {
        TArray<FGameEvent> Events;
        for (TActorIterator<AFactoryVehiclePath> It(World); It; ++It)
            if (const AFactoryTruckGate* Gate = It->GetWaitingGate())
            {
                if (Gate->IsA<AFactoryRollDoor>())
                    Events.Add({TEXT("Camión esperando en el portón"), TEXT("Abrilo con E en la botonera de la columna."), 0});
                else if (Gate->IsA<AFactoryGateBarrier>())
                    Events.Add({It->GetCargoCount() > 0 ? FString::Printf(TEXT("Camión con %d paquetes en la barrera"), It->GetCargoCount())
                                                        : FString(TEXT("Camión esperando en la barrera")),
                                TEXT("Entrá a la cabina y levantala con E."), 0});
                else
                    Events.Add({TEXT("Camión esperando"), TEXT("Algo le cierra el paso."), 0});
            }
        for (TActorIterator<AFactoryDispatchBelt> It(World); It; ++It)
            if (It->bFull && !UFactoryUnlockSubsystem::IsLocked(*It))
                Events.Add({FString::Printf(TEXT("%s de despacho llena"), *It->BeltName.Left(1).ToUpper().Append(It->BeltName.Mid(1).ToLower())),
                            TEXT("Sacá cajas para que vuelva a andar."), 1});
        return Events;
    }

    /** A tiny truck or box, drawn in a circle of radius R. */
    void EventIcon(const FPen& Pen, int32 Kind, FVector2D C, float R, float Alpha)
    {
        const FLinearColor Ink = Hex(0x2B2340, Alpha), White = FLinearColor(1, 1, 1, Alpha);
        Pen.Fill(Circle(C, R + 3), Ink);
        Pen.Fill(Circle(C, R), Kind == 0 ? Hex(0x2F6FD6, Alpha) : Hex(0xFF8A1F, Alpha));
        if (Kind == 0)
        {
            Pen.Rect(C.X - 13, C.Y - 8, 16, 11, White);          // box
            Pen.Rect(C.X + 4, C.Y - 4, 8, 7, White);             // cab
            Pen.Fill(Circle({C.X - 8, C.Y + 6}, 3.2f, 10), White);
            Pen.Fill(Circle({C.X + 7, C.Y + 6}, 3.2f, 10), White);
        }
        else
        {
            Pen.Rect(C.X - 9, C.Y - 9, 18, 18, Hex(0xC89B61, Alpha));
            Pen.Rect(C.X - 2, C.Y - 9, 4, 18, Hex(0xE8C98F, Alpha));
        }
    }
}

bool AFactoryDemoHUD::ClickEvents(float X, float Y)
{
    if (!EventsBadge.bIsValid || !EventsBadge.IsInside(FVector2D(X, Y))) return false;
    bEventsOpen = !bEventsOpen;
    EventsOpenedAt = GetWorld()->GetRealTimeSeconds();
    return true;
}

void AFactoryDemoHUD::DrawEvents(float S, float W, float H)
{
    const float Now = GetWorld()->GetRealTimeSeconds();
    const TArray<FGameEvent> Events = CollectEvents(GetWorld());
    if (Events.Num() > EventsSeen) EventsChangedAt = Now;   // something new: the sign jumps
    EventsSeen = Events.Num();
    FPen Pen{this, Canvas, S, GEngine->GetMediumFont(), GEngine->GetLargeFont()};
    const FLinearColor Cream = Hex(0xFFF4E0), Orange = Hex(0xFF8A1F), Ink = Hex(0x2B2340), Red = Hex(0xE5484D), White = FLinearColor::White;
    const bool bAny = Events.Num() > 0;

    // The sign: a round sticker with "!" and a red count; it jumps when an event appears and sways while there are any.
    const FVector2D C(64, 124);   // debajo del dinero (arriba a la izquierda)
    const float Since = Now - EventsChangedAt;
    const float Jump = Since < .5f ? 1.0f + .35f * (1.0f - EaseOutBack(Since / .5f, 3.0f)) : 1.0f;
    const float Sway = bAny ? 5.0f * FMath::Sin(Now * 3.0f) : 0.0f;
    const float R = 30 * Jump;
    Pen.Fill(Circle(C + FVector2D(4, 5), R + 4), Faded(Ink, .35f));
    Pen.Fill(Circle(C, R + 4), Ink);
    Pen.Fill(Circle(C, R), bAny ? Orange : Cream);
    // "!" as shapes so it can sway: a tapered bar and a dot.
    const FPts Bar = Xf(Quad({C.X - 5, C.Y - 18}, {C.X + 5, C.Y - 18}, {C.X + 3, C.Y + 5}, {C.X - 3, C.Y + 5}), C, Jump, FVector2D::ZeroVector, Sway);
    Pen.Fill(Bar, bAny ? White : Faded(Ink, .45f));
    Pen.Fill(Xf(Circle({C.X, C.Y + 13}, 4.5f, 12), C, Jump, FVector2D::ZeroVector, Sway), bAny ? White : Faded(Ink, .45f));
    if (bAny)
    {
        const FVector2D B(C.X + 24, C.Y - 22);
        Pen.Fill(Circle(B, 15 * Jump), Ink);
        Pen.Fill(Circle(B, 12 * Jump), Red);
        Pen.Centered(FString::FromInt(Events.Num()), B.X, B.Y - 10 * Jump, .85f * Jump, White);
    }
    EventsBadge = FBox2D(FVector2D(C.X - 38, C.Y - 38) * S, FVector2D(C.X + 44, C.Y + 38) * S);
    if (!bEventsOpen) return;

    // Detail: a cream card under the sign, one row per event.
    const float T = Now - EventsOpenedAt;
    const float K = EaseOutBack(T / .3f);
    const float X = 24, Y = 172, CW = 440, Row = 58, CH = 58 + Row * FMath::Max(Events.Num(), 1) + 10;
    const FVector2D Pivot(X + 30, Y);
    Pen.Fill(Xf(RoundRect(X + 6, Y + 6, CW, CH, 20), Pivot, K), Faded(Ink, .35f));
    Pen.Fill(Xf(RoundRect(X - 3, Y - 3, CW + 6, CH + 6, 22), Pivot, K), Ink);
    Pen.Fill(Xf(RoundRect(X, Y, CW, CH, 20), Pivot, K), Cream);
    Pen.Fill(Xf(Quad({X + 18, Y + 1}, {X + 34, Y - 14}, {X + 50, Y + 1}, {X + 34, Y + 1}), Pivot, K), Ink);   // tail toward the sign
    const float In = Clamp01((T - .12f) / .12f);
    Pen.Fill(RoundRect(X + 16, Y + 14, 150, 32, 16), Faded(Orange, In));
    Pen.Text(TEXT("EVENTOS"), X + 34, Y + 20, .9f, Faded(White, In));
    Pen.Text(TEXT("clic en la señal: cerrar"), X + CW - 170, Y + 22, .66f, Faded(Hex(0x8A7F98), In));
    if (!bAny)
        Pen.Text(TEXT("Todo en orden: no hay nada esperando."), X + 22, Y + 66, .85f, Faded(Ink, In));
    for (int32 I = 0; I < Events.Num(); ++I)
    {
        const float RowIn = Clamp01((T - .15f - .05f * I) / .15f);
        const float RY = Y + 58 + I * Row, Slide = 20.0f * (1.0f - EaseOutQuart((T - .15f - .05f * I) / .25f));
        Pen.Fill(RoundRect(X + 14 + Slide, RY, CW - 28, Row - 8, 14), Faded(White, RowIn));
        EventIcon(Pen, Events[I].Kind, {X + 42 + Slide, RY + (Row - 8) / 2}, 17, RowIn);
        Pen.Text(Events[I].Title, X + 72 + Slide, RY + 6, .88f, Faded(Ink, RowIn));
        Pen.Text(Events[I].Hint, X + 72 + Slide, RY + 28, .7f, Faded(Hex(0x5A4E6E), RowIn));
    }
}

void AFactoryDemoHUD::DrawMissionNotice(float S, float W, float H)
{
    const auto* Mission = GetWorld()->GetSubsystem<UFactoryMissionSubsystem>();
    if (!Mission || !Mission->bCompleted) return;
    const float T = GetWorld()->GetTimeSeconds() - Mission->CompletedAt, Life = 7.0f;
    if (T < 0.0f || T > Life) return;
    if (!Portrait) Portrait = LoadObject<UTexture2D>(nullptr, TEXT("/Game/FactoryCtyco/UI/T_RetratoTecJunior.T_RetratoTecJunior"));
    FPen Pen{this, Canvas, S, GEngine->GetMediumFont(), GEngine->GetLargeFont()};
    const FLinearColor Cream = Hex(0xFFF4E0), Orange = Hex(0xFF8A1F), Ink = Hex(0x2B2340), Green = Hex(0x3DD68C), White = FLinearColor::White;
    // Confetti in the character's colours, falling with a little spin (behind the card).
    const FLinearColor Colours[] = {Orange, Hex(0x2F6FD6), Green, Hex(0xFFC928), Hex(0xE5484D)};
    for (int32 I = 0; I < 46; ++I)
    {
        const float Seed = FMath::Frac(FMath::Sin(I * 12.9898f) * 43758.5453f), Seed2 = FMath::Frac(FMath::Sin(I * 78.233f) * 12345.678f);
        const float Start = .1f + Seed2 * .5f, Age = T - Start;
        if (Age < 0) continue;
        const FVector2D P(W / 2 + (Seed - .5f) * 900 + FMath::Sin(Age * 3 + I) * 20, 60 + Age * (120 + Seed2 * 90) + 60 * Age * Age);
        if (P.Y > H) continue;
        const float Spin = Age * (200 + 300 * Seed) * (I % 2 ? 1 : -1);
        Pen.Fill(Xf(Quad(P + FVector2D(-6, -3), P + FVector2D(6, -3), P + FVector2D(6, 3), P + FVector2D(-6, 3)), P, 1.0f, FVector2D::ZeroVector, Spin),
                 Faded(Colours[I % 5], Clamp01((Life - T) / .5f)));
    }
    // The card pops in and shrinks away at the end.
    const float K = T < Life - .25f ? EaseOutBack(T / .4f) : Clamp01((Life - T) / .25f);
    const float CW = 560, CH = 150, X = (W - CW) / 2, Y = 86;
    const FVector2D Pivot(W / 2, Y + CH / 2);
    Pen.Fill(Xf(RoundRect(X + 8, Y + 8, CW, CH, 26), Pivot, K), Faded(Ink, .35f));
    Pen.Fill(Xf(RoundRect(X - 4, Y - 4, CW + 8, CH + 8, 30), Pivot, K), Ink);
    Pen.Fill(Xf(RoundRect(X, Y, CW, CH, 26), Pivot, K), Cream);
    const float In = Clamp01((T - .2f) / .15f);
    // Portrait sticker on the left, bobbing.
    const FVector2D PC(X + 78, Y + CH / 2 + 3 * FMath::Sin(T * 2.4f));
    Pen.Fill(Circle(PC, 60), Faded(Ink, In));
    Pen.Fill(Circle(PC, 56), Faded(Green, In));
    Pen.Fill(Circle(PC, 52), Faded(Hex(0xFFE2B8), In));
    PortraitDisc(Pen, Portrait, PC, 52, In);
    // Green ribbon with the title, and the line under it.
    const float Ribbon = EaseOutBack((T - .25f) / .3f);
    const float RX = X + 160, RW = CW - 184;
    Pen.Fill(Xf(RoundRect(RX - 3, Y + 22 - 3, RW + 6, 56, 18), {RX, Y + 47}, Ribbon), Faded(Ink, In));
    Pen.Fill(Xf(RoundRect(RX, Y + 22, RW, 50, 16), {RX, Y + 47}, Ribbon), Faded(Green, In));
    const float Jump = 1.0f + .06f * FMath::Sin(T * 5.0f) * FMath::Exp(-T * .6f);
    Pen.Centered(TEXT("¡MISIÓN CUMPLIDA!"), RX + RW / 2, Y + 30, 1.35f * Jump * Ribbon, Faded(White, In));
    Pen.Centered(FString::Printf(TEXT("Entregaste %d paquetes. ¡Gran trabajo!"), Mission->Delivered), RX + RW / 2, Y + 94, .92f, Faded(Ink, Clamp01((T - .45f) / .2f)));
}

FBox2D AFactoryDemoHUD::DrawHireCard(float S, float X, float Y, float CW, float Alpha, FVector2D Mouse)
{
    if (!Portrait) Portrait = LoadObject<UTexture2D>(nullptr, TEXT("/Game/FactoryCtyco/UI/T_RetratoTecJunior.T_RetratoTecJunior"));
    FPen Pen{this, Canvas, S, GEngine->GetMediumFont(), GEngine->GetLargeFont()};
    const FLinearColor Orange = Hex(0xFF8A1F), Blue = Hex(0x2F6FD6), Ink = Hex(0x2B2340), Green = Hex(0x3DD68C),
        Muted = Hex(0x5A4E6E), Grey = Hex(0xB9B0C4), White = FLinearColor::White;
    const FName Job(TEXT("Barrera"));
    const UFactoryStaffSubsystem* Staff = UFactoryStaffSubsystem::Get(this);
    const AFactoryWorker* Worker = Staff ? Staff->GetWorker(Job) : nullptr;
    const UFactoryEconomySubsystem* Economy = UFactoryEconomySubsystem::Get(this);
    const int32 Cost = Economy ? Economy->GetHireCost(Job) : 0;
    const int32 Missing = Economy ? FMath::Max(0, Cost - Economy->GetMoney()) : 0;
    const bool bCanHire = Staff && Staff->CanHire(Job) && Missing == 0;
    const float CH = 186;
    // Card: white with ink border and hard shadow.
    Pen.Fill(RoundRect(X + 5, Y + 6, CW, CH, 18), Faded(Ink, .3f * Alpha));
    Pen.Fill(RoundRect(X - 3, Y - 3, CW + 6, CH + 6, 21), Faded(Ink, Alpha));
    Pen.Fill(RoundRect(X, Y, CW, CH, 18), Faded(White, Alpha));
    // Portrait (a copy of TecJunior) in a blue ring; a small cap badge with the job's colour.
    const FVector2D PC(X + 62, Y + 70);
    const float Bob = Worker && Worker->GetState() != EFactoryWorkerState::Working ? 2.5f * FMath::Sin(GetWorld()->GetRealTimeSeconds() * 8.0f) : 0.0f;
    Pen.Fill(Circle(PC + FVector2D(0, Bob), 48), Faded(Ink, Alpha));
    Pen.Fill(Circle(PC + FVector2D(0, Bob), 44), Faded(Worker ? Green : Blue, Alpha));
    Pen.Fill(Circle(PC + FVector2D(0, Bob), 40), Faded(Hex(0xFFE2B8), Alpha));
    PortraitDisc(Pen, Portrait, PC + FVector2D(0, Bob), 40, Alpha);
    Pen.Fill(RoundRect(PC.X - 40, PC.Y + 40, 80, 24, 12), Faded(Ink, Alpha));
    Pen.Centered(TEXT("BARRERA"), PC.X, PC.Y + 43, .62f, Faded(White, Alpha));
    // Name, job and status.
    const float TX = X + 124;
    Pen.Text(TEXT("Encargado de barrera"), TX, Y + 14, 1.0f, Faded(Ink, Alpha));
    Pen.Text(TEXT("Levanta la barrera cuando un camión"), TX, Y + 42, .74f, Faded(Muted, Alpha));
    Pen.Text(TEXT("cargado espera para salir."), TX, Y + 60, .74f, Faded(Muted, Alpha));
    if (Worker)
    {
        Pen.Fill(Circle({TX + 7, Y + 93}, 6, 14), Faded(Green, Alpha));
        Pen.Text(FString::Printf(TEXT("%s · %d camiones"), *Worker->Describe(), Worker->Handled), TX + 20, Y + 84, .74f, Faded(Ink, Alpha));
    }
    else if (Staff && !Staff->CanHire(Job))
        Pen.Text(TEXT("Falta el punto de contratación en el nivel."), TX, Y + 84, .7f, Faded(Muted, Alpha));
    else if (Missing > 0)
        Pen.Text(FString::Printf(TEXT("Te faltan %s para contratarlo."), *UFactoryEconomySubsystem::Format(Missing)), TX, Y + 84, .74f, Faded(Hex(0xE5484D), Alpha));
    else
        Pen.Text(TEXT("Llega en auto al estacionamiento de empleados."), TX, Y + 84, .7f, Faded(Muted, Alpha));
    // Button: orange CONTRATAR that presses under the mouse; green once hired; grey when it cannot.
    const float BX = TX, BY = Y + 118, BW = CW - 124 - 18, BH = 48;
    const bool bHover = bCanHire && Mouse.X >= BX && Mouse.X <= BX + BW && Mouse.Y >= BY && Mouse.Y <= BY + BH;
    const float Lift = bHover ? 2 : 5;
    Pen.Fill(RoundRect(BX + Lift, BY + Lift, BW, BH, 24), Faded(Ink, Alpha));
    Pen.Fill(RoundRect(BX - 3, BY - 3, BW + 6, BH + 6, 27), Faded(Ink, Alpha));
    Pen.Fill(RoundRect(BX, BY, BW, BH, 24), Faded(Worker ? Green : bCanHire ? Orange : Grey, Alpha));
    const FString Label = Worker ? FString(TEXT("CONTRATADO")) : FString::Printf(TEXT("CONTRATAR · %s"), *UFactoryEconomySubsystem::Format(Cost));
    Pen.Centered(Label, BX + BW / 2, BY + 12, 1.0f, Faded(White, Alpha));
    return bCanHire ? FBox2D(FVector2D(BX, BY) * S, FVector2D(BX + BW, BY + BH) * S) : FBox2D(ForceInit);
}

void AFactoryDemoHUD::OpenBooth(AFactoryGateBarrier* Barrier)
{
    if (Barrier == OpenBoothActor.Get()) return;
    OpenBoothActor = Barrier;
    BoothOpenedAt = GetWorld()->GetRealTimeSeconds();
    UpgradeTriedAt = -100.0f;
}

AActor* AFactoryDemoHUD::GetOpenBooth() const
{
    return OpenBoothActor.Get();
}

bool AFactoryDemoHUD::ClickBooth(float X, float Y)
{
    if (!OpenBoothActor.IsValid() || !BoothPanel.bIsValid || !BoothPanel.IsInside(FVector2D(X, Y))) return false;
    const FVector2D At(X, Y);
    if (BoothClose.bIsValid && BoothClose.IsInside(At)) OpenBooth(nullptr);
    else if (BoothHire.bIsValid && BoothHire.IsInside(At)) { if (auto* Staff = UFactoryStaffSubsystem::Get(this)) Staff->Hire(TEXT("Barrera")); }
    else if (BoothUpgrade.bIsValid && BoothUpgrade.IsInside(At)) UpgradeTriedAt = GetWorld()->GetRealTimeSeconds();
    return true;   // a click on the panel never goes through to the world
}

void AFactoryDemoHUD::DrawBoothPanel(float S, float W, float H)
{
    BoothPanel = BoothHire = BoothUpgrade = BoothClose = FBox2D(ForceInit);
    const AFactoryGateBarrier* Barrier = OpenBoothActor.Get();
    if (!Barrier) return;
    const float Now = GetWorld()->GetRealTimeSeconds(), T = Now - BoothOpenedAt;
    FPen Pen{this, Canvas, S, GEngine->GetMediumFont(), GEngine->GetLargeFont()};
    const FLinearColor Cream = Hex(0xFFF4E0), Orange = Hex(0xFF8A1F), Blue = Hex(0x2F6FD6), Ink = Hex(0x2B2340),
        Green = Hex(0x3DD68C), Purple = Hex(0x8B5CF6), Muted = Hex(0x5A4E6E), White = FLinearColor::White;
    FVector2D Mouse(-1, -1);
    float MX = -1, MY = -1;
    if (PlayerOwner && PlayerOwner->GetMousePosition(MX, MY)) Mouse = FVector2D(MX, MY) / S;
    const float CW = 470, CH = 520, X = W - CW - 30, Y = FMath::Max(90.0f, (H - CH) / 2 - 10);
    const float K = EaseOutBack(T / .3f);
    const FVector2D Pivot(X + CW, Y + CH / 2);
    Pen.Fill(Xf(RoundRect(X + 8, Y + 8, CW, CH, 26), Pivot, K), Faded(Ink, .35f));
    Pen.Fill(Xf(RoundRect(X - 4, Y - 4, CW + 8, CH + 8, 30), Pivot, K), Ink);
    Pen.Fill(Xf(RoundRect(X, Y, CW, CH, 26), Pivot, K), Cream);
    BoothPanel = FBox2D(FVector2D(X - 4, Y - 30) * S, FVector2D(X + CW + 4, Y + CH + 4) * S);
    if (K < .98f) return;
    const float In = Clamp01((T - .25f) / .15f);
    // Title ribbon (orange) sticking out of the top, and a round close button.
    Pen.Fill(RoundRect(X + 22, Y - 22, 300, 50, 16), Faded(Ink, In));
    Pen.Fill(RoundRect(X + 25, Y - 19, 294, 44, 14), Faded(Orange, In));
    Pen.Text(TEXT("CABINA DE LA BARRERA"), X + 42, Y - 8, 1.0f, Faded(White, In));
    const FVector2D XC(X + CW - 30, Y + 28);
    const bool bCloseHover = FVector2D::Distance(Mouse, XC) < 18;
    Pen.Fill(Circle(XC, 19), Faded(Ink, In));
    Pen.Fill(Circle(XC, 16), Faded(bCloseHover ? Hex(0xE5484D) : White, In));
    Pen.Centered(TEXT("X"), XC.X, XC.Y - 10, .85f, Faded(bCloseHover ? White : Ink, In));
    BoothClose = FBox2D((XC - FVector2D(19, 19)) * S, (XC + FVector2D(19, 19)) * S);
    // Data: four rows with a coloured chip each.
    int32 Waiting = 0;
    for (TActorIterator<AFactoryVehiclePath> It(GetWorld()); It; ++It)
        if (!UFactoryUnlockSubsystem::IsLocked(*It) && It->GetWaitingGate() == Barrier) ++Waiting;
    const UFactoryStaffSubsystem* Staff = UFactoryStaffSubsystem::Get(this);
    const AFactoryWorker* Worker = Staff ? Staff->GetWorker(TEXT("Barrera")) : nullptr;
    const FString State = Barrier->Openness >= .999f ? TEXT("ARRIBA") : Barrier->Openness <= .001f ? TEXT("ABAJO")
        : Barrier->bWantOpen ? TEXT("SUBIENDO") : TEXT("BAJANDO");
    struct FRow { const TCHAR* Name; FString Value; FLinearColor Chip; };
    const FRow Rows[] = {
        {TEXT("Barrera"), State, Barrier->bWantOpen ? Green : Orange},
        {TEXT("Camiones esperando"), FString::FromInt(Waiting), Waiting > 0 ? Hex(0xE5484D) : Green},
        {TEXT("Camiones que salieron"), FString::FromInt(Barrier->Passed), Blue},
        {TEXT("Encargado"), Worker ? TEXT("Contratado") : TEXT("Sin contratar"), Worker ? Green : Hex(0xB9B0C4)}};
    for (int32 I = 0; I < 4; ++I)
    {
        const float RY = Y + 52 + I * 40, RowIn = Clamp01((T - .3f - .05f * I) / .15f);
        Pen.Fill(RoundRect(X + 20, RY, CW - 40, 34, 12), Faded(White, RowIn));
        Pen.Fill(Circle({X + 40, RY + 17}, 7, 14), Faded(Rows[I].Chip, RowIn));
        Pen.Text(Rows[I].Name, X + 56, RY + 8, .8f, Faded(Muted, RowIn));
        Pen.Text(Rows[I].Value, X + CW - 36 - Pen.Width(Rows[I].Value, .85f), RY + 7, .85f, Faded(Ink, RowIn));
    }
    // Hire card, as on the info panel's hire page.
    BoothHire = DrawHireCard(S, X + 20, Y + 230, CW - 40, Clamp01((T - .45f) / .15f), Mouse);
    // Upgrade: purple, with a "PRONTO" badge; a click only says it is coming.
    const float UX = X + 20, UY = Y + 440, UW = CW - 40, UH = 50, UIn = Clamp01((T - .55f) / .15f);
    const bool bUpHover = Mouse.X >= UX && Mouse.X <= UX + UW && Mouse.Y >= UY && Mouse.Y <= UY + UH;
    const float Lift = bUpHover ? 2 : 5;
    Pen.Fill(RoundRect(UX + Lift, UY + Lift, UW, UH, 25), Faded(Ink, UIn));
    Pen.Fill(RoundRect(UX - 3, UY - 3, UW + 6, UH + 6, 28), Faded(Ink, UIn));
    Pen.Fill(RoundRect(UX, UY, UW, UH, 25), Faded(Purple, UIn));
    Pen.Text(TEXT("MEJORAR CABINA"), UX + 24, UY + 13, 1.0f, Faded(White, UIn));
    Pen.Fill(RoundRect(UX + UW - 110, UY + 11, 92, 28, 14), Faded(White, UIn));
    Pen.Centered(TEXT("PRONTO"), UX + UW - 64, UY + 15, .7f, Faded(Purple, UIn));
    BoothUpgrade = FBox2D(FVector2D(UX, UY) * S, FVector2D(UX + UW, UY + UH) * S);
    if (Now - UpgradeTriedAt < 2.0f)
        Pen.Centered(TEXT("Las mejoras llegan pronto."), X + CW / 2, UY + UH + 10, .75f, Faded(Muted, Clamp01((2.0f - (Now - UpgradeTriedAt)) / .3f)));
}
