// Canvas drawing helpers shared by the HUD panels ("Pegatina Pop" look): shapes in design units (x S = pixels),
// easing curves and colours. Moved out of FactoryInfoPanel.cpp so the guide (FactoryGuideHUD.cpp) can use them.
#pragma once

#include "CoreMinimal.h"
#include "CanvasItem.h"
#include "Engine/Canvas.h"
#include "Engine/Font.h"
#include "Engine/Texture2D.h"
#include "GameFramework/HUD.h"
#include "GlobalRenderResources.h"

namespace FactoryHudDraw
{
    using FPts = TArray<FVector2D>;

    inline float Clamp01(float X) { return FMath::Clamp(X, 0.0f, 1.0f); }
    inline float EaseOutBack(float X, float Overshoot = 1.70158f) { X = Clamp01(X) - 1.0f; return 1.0f + (Overshoot + 1.0f) * X * X * X + Overshoot * X * X; }
    inline float EaseOutQuart(float X) { X = 1.0f - Clamp01(X); return 1.0f - X * X * X * X; }
    inline FLinearColor Hex(uint32 RGB, float Alpha = 1.0f)
    {
        return FLinearColor(FColor((RGB >> 16) & 255, (RGB >> 8) & 255, RGB & 255)) .CopyWithNewOpacity(Alpha);
    }
    inline FLinearColor Faded(FLinearColor C, float Alpha) { C.A *= Clamp01(Alpha); return C; }

    inline FPts RoundRect(float X, float Y, float W, float H, float R, int32 Seg = 5)
    {
        R = FMath::Min(R, FMath::Min(W, H) / 2);
        FPts P;
        const FVector2D Centers[4] = {{X + W - R, Y + R}, {X + W - R, Y + H - R}, {X + R, Y + H - R}, {X + R, Y + R}};
        for (int32 Corner = 0; Corner < 4; ++Corner)
            for (int32 I = 0; I <= Seg; ++I)
            {
                const float A = (-90.0f + 90.0f * Corner + 90.0f * I / Seg) * PI / 180.0f;
                P.Add(Centers[Corner] + FVector2D(FMath::Cos(A), FMath::Sin(A)) * R);
            }
        return P;
    }
    inline FPts Circle(FVector2D C, float R, int32 N = 40)
    {
        FPts P;
        for (int32 I = 0; I < N; ++I) P.Add(C + FVector2D(FMath::Cos(2 * PI * I / N), FMath::Sin(2 * PI * I / N)) * R);
        return P;
    }
    inline FPts Quad(FVector2D A, FVector2D B, FVector2D C, FVector2D D) { return {A, B, C, D}; }
    /** Scales about Pivot, rotates (degrees) and moves. */
    inline FPts Xf(const FPts& In, FVector2D Pivot, float Scale, FVector2D Offset = FVector2D::ZeroVector, float Degrees = 0.0f)
    {
        FPts Out;
        const float Cs = FMath::Cos(Degrees * PI / 180.0f), Sn = FMath::Sin(Degrees * PI / 180.0f);
        for (const FVector2D& P : In)
        {
            const FVector2D D = (P - Pivot) * Scale;
            Out.Add(Pivot + FVector2D(D.X * Cs - D.Y * Sn, D.X * Sn + D.Y * Cs) + Offset);
        }
        return Out;
    }
    /** Draws in design units (x S = pixels). */
    struct FPen
    {
        AHUD* Hud = nullptr;
        UCanvas* Canvas = nullptr;
        float S = 1.0f;
        UFont* Font = nullptr;
        UFont* Big = nullptr;

        void Fill(const FPts& P, FLinearColor Color, UTexture2D* Texture = nullptr, FBox2D UVBox = FBox2D(ForceInit)) const
        {
            if (P.Num() < 3 || Color.A <= 0.001f) return;
            FVector2D Centre = FVector2D::ZeroVector;
            for (const FVector2D& V : P) Centre += V;
            Centre /= P.Num();
            auto UV = [&](FVector2D V) { return UVBox.bIsValid ? (V - UVBox.Min) / (UVBox.Max - UVBox.Min) : FVector2D::ZeroVector; };
            TArray<FCanvasUVTri> Tris;
            for (int32 I = 0; I < P.Num(); ++I)
            {
                FCanvasUVTri T;
                T.V0_Pos = Centre * S; T.V1_Pos = P[I] * S; T.V2_Pos = P[(I + 1) % P.Num()] * S;
                T.V0_UV = UV(Centre); T.V1_UV = UV(P[I]); T.V2_UV = UV(P[(I + 1) % P.Num()]);
                T.V0_Color = T.V1_Color = T.V2_Color = Color;
                Tris.Add(T);
            }
            const FTexture* Resource = Texture && Texture->GetResource() ? Texture->GetResource() : GWhiteTexture;
            FCanvasTriangleItem Item(Tris, Resource);
            Item.BlendMode = SE_BLEND_Translucent;
            Canvas->DrawItem(Item);
        }
        void Rect(float X, float Y, float W, float H, FLinearColor Color) const
        {
            if (Color.A > 0.001f) Hud->DrawRect(Color, X * S, Y * S, W * S, H * S);
        }
        float Width(const FString& Value, float Scale, bool bBig = false) const
        {
            float W = 0, H = 0;
            Hud->GetTextSize(Value, W, H, bBig ? Big : Font, Scale * S);
            return W / S;
        }
        void Text(const FString& Value, float X, float Y, float Scale, FLinearColor Color, bool bBig = false) const
        {
            if (Color.A > 0.001f) Hud->DrawText(Value, Color, X * S, Y * S, bBig ? Big : Font, Scale * S);
        }
        void Centered(const FString& Value, float CX, float Y, float Scale, FLinearColor Color, bool bBig = false) const
        {
            Text(Value, CX - Width(Value, Scale, bBig) / 2, Y, Scale, Color, bBig);
        }
    };

    /** The portrait in a disc (textured triangles), faded by Alpha. */
    inline void PortraitDisc(const FPen& Pen, UTexture2D* Texture, FVector2D Centre, float R, float Alpha)
    {
        if (!Texture || !Texture->GetResource()) return;
        const FPts Disc = Circle(Centre, R, 40);
        TArray<FCanvasUVTri> Tris;
        for (int32 I = 0; I < Disc.Num(); ++I)
        {
            const int32 J = (I + 1) % Disc.Num();
            FCanvasUVTri Tri;
            Tri.V0_Pos = Centre * Pen.S; Tri.V1_Pos = Disc[I] * Pen.S; Tri.V2_Pos = Disc[J] * Pen.S;
            Tri.V0_UV = FVector2D(.5f, .5f);
            Tri.V1_UV = (Disc[I] - Centre) / (2 * R) + FVector2D(.5f, .5f);
            Tri.V2_UV = (Disc[J] - Centre) / (2 * R) + FVector2D(.5f, .5f);
            Tri.V0_Color = Tri.V1_Color = Tri.V2_Color = FLinearColor(1, 1, 1, Alpha);
            Tris.Add(Tri);
        }
        FCanvasTriangleItem Item(Tris, Texture->GetResource());
        Item.BlendMode = SE_BLEND_Translucent;
        Pen.Canvas->DrawItem(Item);
    }
}
