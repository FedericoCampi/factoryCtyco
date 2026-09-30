#pragma once
#include "GrowEvolution.h"

namespace GrowRules
{
    struct FRequirement
    {
        EGrowDecision Source;
        int32 Level;
    };
    inline EGrowDecision Primary(EGrowProfession Role)
    {
        return Role==EGrowProfession::Caretaker?EGrowDecision::Water:
            Role==EGrowProfession::Courier?EGrowDecision::Logistics:EGrowDecision::Recycling;
    }
    inline EGrowDecision Support(EGrowProfession Role)
    {
        return Role==EGrowProfession::Caretaker?EGrowDecision::Habitat:
            Role==EGrowProfession::Courier?EGrowDecision::Recycling:EGrowDecision::Logistics;
    }
    inline FString Name(EGrowDecision Decision)
    {
        return Decision==EGrowDecision::Awaken?TEXT("Robots"):AGrowEvolutionWorld::DecisionName(Decision);
    }
    /** Level-one systems bootstrap a connected network; higher levels require contributions from peers. */
    inline TArray<FRequirement> Requirements(EGrowDecision Target,int32 NextLevel,EGrowProfession Role)
    {
        using D=EGrowDecision;
        switch(Target)
        {
            case D::Recycling: return NextLevel==2?TArray<FRequirement>{{D::Energy,2},{D::Water,1}}:
                TArray<FRequirement>{{D::Logistics,2},{D::Awaken,2}};
            case D::Water: return NextLevel==2?TArray<FRequirement>{{D::Energy,1}}:
                TArray<FRequirement>{{D::Habitat,2},{D::Logistics,1}};
            case D::Logistics: return NextLevel==2?TArray<FRequirement>{{D::Energy,1},{D::Recycling,1}}:
                TArray<FRequirement>{{D::Awaken,2},{D::Habitat,1}};
            case D::Energy: return NextLevel==2?TArray<FRequirement>{{D::Water,1},{D::Recycling,1}}:
                TArray<FRequirement>{{D::Logistics,2},{D::Awaken,2}};
            case D::Habitat: return NextLevel==2?TArray<FRequirement>{{D::Water,2},{D::Recycling,1}}:
                TArray<FRequirement>{{D::Awaken,2},{D::Logistics,2}};
            case D::Awaken: return NextLevel==2?TArray<FRequirement>{{D::Energy,1},{Primary(Role),2}}:
                TArray<FRequirement>{{D::Energy,2},{Primary(Role),2},{Support(Role),2},{D::Habitat,1}};
            default:return {};
        }
    }
    inline bool Ready(EGrowDecision Target,const TArray<int32>& Levels,EGrowProfession Role)
    {
        const int32 Index=static_cast<int32>(Target);
        if(!Levels.IsValidIndex(Index)||Levels[Index]<1||Levels[Index]>=3)return false;
        if(Target==EGrowDecision::Awaken&&Role==EGrowProfession::Apprentice)return false;
        for(const auto& Required:Requirements(Target,Levels[Index]+1,Role))
            if(Levels[static_cast<int32>(Required.Source)]<Required.Level)return false;
        return true;
    }
    inline FString Contribution(EGrowDecision Source,EGrowDecision Target)
    {
        switch(Source)
        {
            case EGrowDecision::Recycling:return TEXT("piezas recuperadas");
            case EGrowDecision::Water:return Target==EGrowDecision::Habitat?TEXT("riego"):TEXT("refrigeración");
            case EGrowDecision::Logistics:return TEXT("distribución de suministros");
            case EGrowDecision::Energy:return TEXT("electricidad");
            case EGrowDecision::Habitat:return Target==EGrowDecision::Water?TEXT("filtrado natural"):TEXT("refugio y mantenimiento");
            default:return TEXT("trabajo de la colonia");
        }
    }
    inline TArray<FGrowUpgrade> Plan(const TArray<EGrowDecision>& History,TArray<int32> Levels,EGrowProfession Role)
    {
        TArray<FGrowUpgrade> Result;
        if(History.IsEmpty())return Result;
        // A choice grants one development opportunity to each older system, preserving GROW order.
        bool Advanced[6]={false,false,false,false,false,false};
        Advanced[static_cast<int32>(History.Last())]=true;
        EGrowDecision LastChanged=History.Last();
        for(int32 Pass=0;Pass<6;++Pass)
        {
            bool bFound=false;
            for(EGrowDecision Target:History)
            {
                const int32 Index=static_cast<int32>(Target);
                if(Advanced[Index]||!Ready(Target,Levels,Role))continue;
                const auto Required=Requirements(Target,Levels[Index]+1,Role);
                EGrowDecision Source=Required[0].Source;
                int32 Latest=-1;
                for(const auto& Need:Required)
                {
                    const int32 Position=History.Find(Need.Source);
                    if(Position>Latest){Source=Need.Source;Latest=Position;}
                    if(Need.Source==LastChanged){Source=LastChanged;break;}
                }
                FGrowUpgrade Upgrade;
                Upgrade.Source=Source;Upgrade.Target=Target;Upgrade.Level=++Levels[Index];
                Upgrade.Reason=FString::Printf(TEXT("%s → %s: %s. Nivel %d."),*Name(Source),*Name(Target),*Contribution(Source,Target),Upgrade.Level);
                Result.Add(Upgrade);
                Advanced[Index]=true;LastChanged=Target;bFound=true;
                break; // Re-evaluate dependants after each actual improvement.
            }
            if(!bFound)break;
        }
        return Result;
    }
}
