#include "GrowEvolution.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/UObjectGlobals.h"

namespace
{
    using FConnectionRoute = TArray<FVector, TInlineAllocator<3>>;

    bool SamePair(EGrowDecision A, EGrowDecision B, EGrowDecision C, EGrowDecision D)
    {
        return (A == C && B == D) || (A == D && B == C);
    }

    FConnectionRoute ConnectionRoute(EGrowDecision Source, EGrowDecision Target)
    {
        FVector Start = AGrowEvolutionWorld::Station(Source);
        FVector End = AGrowEvolutionWorld::Station(Target);
        // Slightly stagger intersecting ribbons to avoid coplanar flickering.
        const float Height = 14.f + .035f * (static_cast<uint8>(Source) * 6 + static_cast<uint8>(Target));
        Start.Z = End.Z = Height;
        FVector Hub = AGrowEvolutionWorld::Station(EGrowDecision::Awaken);
        Hub.Z = Height;
        const FVector Direction = (End - Start).GetSafeNormal();
        constexpr float SocketRadius = 158.f;
        FConnectionRoute Route;
        const FVector Nearest = FMath::ClosestPointOnSegment(Hub, Start, End);
        if (Source != EGrowDecision::Awaken && Target != EGrowDecision::Awaken &&
            FVector::DistSquared2D(Nearest, Hub) < FMath::Square(190.f))
        {
            // Outer systems must not send their visual pulse through the cradle.
            FVector Side(-Direction.Y, Direction.X, 0);
            if (FVector::DotProduct((Start + End) * .5f - Hub, Side) < 0) Side *= -1;
            const FVector Corner = Hub + Side * 215.f;
            Route.Add(Start + (Corner - Start).GetSafeNormal() * SocketRadius);
            Route.Add(Corner);
            Route.Add(End + (Corner - End).GetSafeNormal() * SocketRadius);
        }
        else
        {
            Route.Add(Start + Direction * SocketRadius);
            Route.Add(End - Direction * SocketRadius);
        }
        return Route;
    }

    FVector SampleRoute(const FConnectionRoute& Route, float Progress, FVector& Tangent)
    {
        float TotalLength = 0;
        for (int32 Index = 1; Index < Route.Num(); ++Index)
            TotalLength += FVector::Distance(Route[Index - 1], Route[Index]);
        float Distance = FMath::Clamp(Progress, 0.f, 1.f) * TotalLength;
        for (int32 Index = 1; Index < Route.Num(); ++Index)
        {
            const FVector Segment = Route[Index] - Route[Index - 1];
            const float Length = Segment.Size();
            if (Distance <= Length || Index == Route.Num() - 1)
            {
                Tangent = Segment.GetSafeNormal();
                return FMath::Lerp(Route[Index - 1], Route[Index],
                    FMath::Clamp(Distance / FMath::Max(Length, 1.f), 0.f, 1.f));
            }
            Distance -= Length;
        }
        Tangent = FVector::ForwardVector;
        return Route[0];
    }

    UStaticMeshComponent* ConnectionPart(AGrowEvolutionWorld* Owner, USceneComponent* Parent,
        UStaticMesh* Mesh, const FString& Name, UMaterialInstanceDynamic* Material)
    {
        const FName UniqueName = MakeUniqueObjectName(Owner, UStaticMeshComponent::StaticClass(), FName(*Name));
        auto* Part = NewObject<UStaticMeshComponent>(Owner, UniqueName, RF_Transient);
        Part->SetupAttachment(Parent);
        Part->SetMobility(EComponentMobility::Movable);
        Part->SetStaticMesh(Mesh);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetGenerateOverlapEvents(false);
        Part->SetCanEverAffectNavigation(false);
        Part->SetCastShadow(false);
        if (Material) Part->SetMaterial(0, Material);
        Part->RegisterComponent();
        return Part;
    }

    UMaterialInstanceDynamic* ConnectionMaterial(AGrowEvolutionWorld* Owner, UMaterialInterface* Parent)
    {
        auto* Material = UMaterialInstanceDynamic::Create(Parent, Owner);
        Material->SetVectorParameterValue(TEXT("BaseColor"), FLinearColor(.035f, .065f, .075f));
        Material->SetVectorParameterValue(TEXT("Emission"), FLinearColor::Black);
        Material->SetScalarParameterValue(TEXT("Metallic"), .15f);
        Material->SetScalarParameterValue(TEXT("Roughness"), .6f);
        return Material;
    }
}

void AGrowEvolutionWorld::BuildConnections()
{
    // Rebuilding is safe when authoring or restarting: these components belong
    // solely to the connection presentation, never to stations or creatures.
    for (FGrowConnectionVisual& Visual : ConnectionVisuals)
    {
        if (IsValid(Visual.Path))
        {
            TArray<USceneComponent*> PathChildren;
            Visual.Path->GetChildrenComponents(true, PathChildren);
            for (USceneComponent* Child : PathChildren) if (IsValid(Child)) Child->DestroyComponent();
            Visual.Path->DestroyComponent();
        }
        if (IsValid(Visual.Pulse)) Visual.Pulse->DestroyComponent();
    }
    ConnectionVisuals.Reset();
    if (!BoxMesh || !DetailMaterial || !RootComponent) return;

    TSet<uint16> CreatedPairs;
    for (const FGrowInteraction& Interaction : Interactions)
    {
        const uint8 A = static_cast<uint8>(Interaction.Source);
        const uint8 B = static_cast<uint8>(Interaction.Target);
        if (A >= 6 || B >= 6 || A == B) continue;
        const uint8 Low = FMath::Min(A, B);
        const uint8 High = FMath::Max(A, B);
        const uint16 Key = Low * 6 + High;
        if (CreatedPairs.Contains(Key)) continue;
        CreatedPairs.Add(Key);

        FGrowConnectionVisual Visual;
        Visual.Source = static_cast<EGrowDecision>(Low);
        Visual.Target = static_cast<EGrowDecision>(High);
        const FString Name = FString::Printf(TEXT("GrowLink_%d_%d"), Low, High);
        auto* PathMaterial = ConnectionMaterial(this, DetailMaterial);
        // A unit-scale meshless anchor groups one or two ribbon segments. Its
        // material override retains the shared MID used by all of its segments.
        Visual.Path = ConnectionPart(this, RootComponent, nullptr, Name, PathMaterial);
        const FConnectionRoute Route = ConnectionRoute(Visual.Source, Visual.Target);
        for (int32 Index = 1; Index < Route.Num(); ++Index)
        {
            const FVector Delta = Route[Index] - Route[Index - 1];
            auto* Segment = ConnectionPart(this, Visual.Path, BoxMesh,
                Name + FString::Printf(TEXT("_Segment_%d"), Index), PathMaterial);
            Segment->SetRelativeLocation((Route[Index] + Route[Index - 1]) * .5f);
            Segment->SetRelativeRotation(Delta.Rotation());
            Segment->SetRelativeScale3D(FVector(Delta.Size(), 5.f, 1.2f) / 100.f);
        }
        auto* PulseMaterial = ConnectionMaterial(this, DetailMaterial);
        Visual.Pulse = ConnectionPart(this, RootComponent, CylinderMesh ? CylinderMesh.Get() : BoxMesh.Get(),
            Name + TEXT("_Pulse"), PulseMaterial);
        Visual.Pulse->SetRelativeScale3D(FVector(.24f, .11f, .032f));
        Visual.Path->SetVisibility(false, true);
        Visual.Pulse->SetVisibility(false);
        ConnectionVisuals.Add(Visual);
    }
    UpdateConnections(0);
}

void AGrowEvolutionWorld::UpdateConnections(float DeltaSeconds)
{
    for (FGrowConnectionVisual& Visual : ConnectionVisuals)
    {
        if (!IsValid(Visual.Path) || !IsValid(Visual.Pulse)) continue;
        const bool bCreated = DecisionLevel(Visual.Source) > 0 && DecisionLevel(Visual.Target) > 0;
        const bool bPending = bCreated && bResolving &&
            SamePair(Visual.Source, Visual.Target, PendingSource, PendingDecision);
        bool bActive = false;
        for (const FGrowInteraction& Interaction : Interactions)
        {
            if (Interaction.bActive && SamePair(Visual.Source, Visual.Target, Interaction.Source, Interaction.Target))
            {
                bActive = true;
                break;
            }
        }
        // Simulation owns ActiveLinks. Rendering only reads the current rules.
        Visual.Path->SetVisibility(bCreated, true);
        Visual.Pulse->SetVisibility(bPending);
        if (!bCreated) continue;

        const FLinearColor SourceColor = DecisionColor(Visual.Source);
        const FLinearColor TargetColor = DecisionColor(Visual.Target);
        const FLinearColor PairColor = FMath::Lerp(SourceColor, TargetColor, .5f);
        if (auto* Material = Cast<UMaterialInstanceDynamic>(Visual.Path->GetMaterial(0)))
        {
            const FLinearColor Emission = PairColor * (bPending ? .62f : bActive ? .11f : .035f);
            const float Blend = 1.f - FMath::Exp(-FMath::Max(DeltaSeconds, 0.f) * 10.f);
            Material->SetVectorParameterValue(TEXT("BaseColor"), PairColor * (bPending ? .28f : .12f));
            Material->SetVectorParameterValue(TEXT("Emission"),
                FMath::Lerp(Material->K2_GetVectorParameterValue(TEXT("Emission")), Emission, Blend));
        }
        if (!bPending) continue;

        const float Progress = FMath::Clamp(1.f - EvolutionCountdown / FMath::Max(ActiveUpgradeDuration, .1f), 0.f, 1.f);
        // One travel per queued reaction, including a reverse direction on the
        // same shared path. Arrival is tied to the actual upgrade countdown.
        const bool bReverse = PendingSource != Visual.Source;
        const float AlongRoute = bReverse ? 1.f - Progress : Progress;
        const FConnectionRoute Route = ConnectionRoute(Visual.Source, Visual.Target);
        FVector Tangent;
        FVector Position = SampleRoute(Route, AlongRoute, Tangent);
        Position.Z += 3.2f;
        if (bReverse) Tangent *= -1;
        Visual.Pulse->SetRelativeLocation(Position);
        Visual.Pulse->SetRelativeRotation(Tangent.Rotation());
        const float Breath = 1.f + .12f * FMath::Sin(Progress * PI);
        Visual.Pulse->SetRelativeScale3D(FVector(.24f, .11f, .032f) * Breath);
        if (auto* Material = Cast<UMaterialInstanceDynamic>(Visual.Pulse->GetMaterial(0)))
        {
            const FLinearColor Color = FMath::Lerp(DecisionColor(PendingSource), DecisionColor(PendingDecision), Progress);
            Material->SetVectorParameterValue(TEXT("BaseColor"), Color * .6f);
            Material->SetVectorParameterValue(TEXT("Emission"), Color * 2.2f);
        }
    }
}
