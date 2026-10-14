#pragma once

#include "CoreMinimal.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

/**
 * Posts under a raised belt (factory belts and loading belts). From each point in Tops (the belt's underside, in the
 * world) a post goes straight down to the floor, when the floor is at least MinGap below. Mesh is stretched from the
 * floor to the point; Width (cm) sets its width, 0 keeps the mesh's own. The instances are placed in world space, so
 * Supports must use absolute location, rotation and scale. Returns how many points found no floor below.
 */
inline int32 FactoryPlaceSupports(UInstancedStaticMeshComponent* Supports, const AActor* Owner, UStaticMesh* Mesh,
                                 UMaterialInterface* Material, const TArray<FVector>& Tops, float Width, float MinGap)
{
    if (!Supports) return 0;
    Supports->ClearInstances();
    Supports->SetWorldTransform(FTransform::Identity);
    if (!Mesh || !Owner || !Owner->GetWorld()) return 0;
    if (Supports->GetStaticMesh() != Mesh) Supports->SetStaticMesh(Mesh);
    if (Material) Supports->SetMaterial(0, Material);
    const FBox Bounds = Mesh->GetBoundingBox();
    const FVector Size = Bounds.GetSize();
    if (Size.Z < KINDA_SMALL_NUMBER) return 0;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BeltSupports), false, Owner);
    const FRotator Turn(0, Owner->GetActorRotation().Yaw, 0);
    int32 Missed = 0;
    for (const FVector& Top : Tops)
    {
        FHitResult Hit;
        if (!Owner->GetWorld()->LineTraceSingleByChannel(Hit, Top - FVector(0, 0, 2), Top - FVector(0, 0, 3000), ECC_Visibility, Params)) { ++Missed; continue; }
        const float Gap = Top.Z - Hit.ImpactPoint.Z;
        if (Gap < MinGap) continue;
        const FVector Scale(Width > 0.0f ? Width / FMath::Max(Size.X, 1.0f) : 1.0f,
                            Width > 0.0f ? Width / FMath::Max(Size.Y, 1.0f) : 1.0f, Gap / Size.Z);
        const FVector Offset = Turn.RotateVector(FVector(Bounds.GetCenter().X * Scale.X, Bounds.GetCenter().Y * Scale.Y, 0));
        Supports->AddInstance(FTransform(Turn, FVector(Top.X - Offset.X, Top.Y - Offset.Y, Hit.ImpactPoint.Z - Bounds.Min.Z * Scale.Z), Scale), true);
    }
    return Missed;
}
