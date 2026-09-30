#include "GrowEvolution.h"
#include "GrowEvolutionRules.h"
#include "FactoryCameraComponent.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/InputComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace
{
    bool ValidDecision(EGrowDecision Decision) { return static_cast<uint8>(Decision) < 6; }
    EGrowDecision PrimaryFor(EGrowProfession Role)
    {
        return Role == EGrowProfession::Caretaker ? EGrowDecision::Water :
            Role == EGrowProfession::Courier ? EGrowDecision::Logistics : EGrowDecision::Recycling;
    }
    EGrowDecision SupportFor(EGrowProfession Role)
    {
        return Role == EGrowProfession::Caretaker ? EGrowDecision::Habitat :
            Role == EGrowProfession::Courier ? EGrowDecision::Recycling : EGrowDecision::Logistics;
    }
    EGrowProfession RoleFor(EGrowDecision Decision)
    {
        return Decision == EGrowDecision::Recycling ? EGrowProfession::Builder :
            Decision == EGrowDecision::Water ? EGrowProfession::Caretaker :
            Decision == EGrowDecision::Logistics ? EGrowProfession::Courier : EGrowProfession::Apprentice;
    }
}

AGrowEvolutionWorld::AGrowEvolutionWorld()
{
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("EvolutionRoot"));
    SystemLevels.Init(0,6);
    LastEvent = TEXT("Un pequeño mundo espera tus decisiones.");
}

bool AGrowEvolutionWorld::HasDecision(EGrowDecision Decision) const { return History.Contains(Decision); }
int32 AGrowEvolutionWorld::DecisionLevel(EGrowDecision Decision) const
{
    return ValidDecision(Decision) && SystemLevels.IsValidIndex(static_cast<int32>(Decision)) ? SystemLevels[static_cast<int32>(Decision)] : 0;
}
bool AGrowEvolutionWorld::IsComplete() const { return History.Num() == 6 && !bResolving && TransitionRemaining <= 0; }
bool AGrowEvolutionWorld::IsSuccessful() const { return IsComplete() && CreatureLevel == 3; }

FString AGrowEvolutionWorld::DecisionName(EGrowDecision Decision)
{
    switch (Decision)
    {
        case EGrowDecision::Recycling: return TEXT("Reciclaje");
        case EGrowDecision::Water: return TEXT("Agua");
        case EGrowDecision::Logistics: return TEXT("Transporte");
        case EGrowDecision::Energy: return TEXT("Energía");
        case EGrowDecision::Habitat: return TEXT("Hábitat");
        case EGrowDecision::Awaken: return TEXT("Despertar");
        default: return TEXT("");
    }
}
FString AGrowEvolutionWorld::DecisionDescription(EGrowDecision Decision)
{
    switch (Decision)
    {
        case EGrowDecision::Recycling: return TEXT("Aprender a construir");
        case EGrowDecision::Water: return TEXT("Aprender a cuidar");
        case EGrowDecision::Logistics: return TEXT("Aprender a repartir");
        case EGrowDecision::Energy: return TEXT("Impulsar la evolución");
        case EGrowDecision::Habitat: return TEXT("Dar lugar a la vida");
        case EGrowDecision::Awaken: return TEXT("Descubrir su vocación");
        default: return TEXT("");
    }
}
FString AGrowEvolutionWorld::ProfessionName(EGrowProfession Value)
{
    switch (Value)
    {
        case EGrowProfession::Builder: return TEXT("Constructores");
        case EGrowProfession::Caretaker: return TEXT("Cuidadores");
        case EGrowProfession::Courier: return TEXT("Transportistas");
        default: return TEXT("Aprendices");
    }
}
FLinearColor AGrowEvolutionWorld::DecisionColor(EGrowDecision Decision)
{
    switch (Decision)
    {
        case EGrowDecision::Recycling: return FLinearColor(1,.43f,.12f);
        case EGrowDecision::Water: return FLinearColor(.10f,.69f,.95f);
        case EGrowDecision::Logistics: return FLinearColor(.43f,.51f,1);
        case EGrowDecision::Energy: return FLinearColor(1,.79f,.20f);
        case EGrowDecision::Habitat: return FLinearColor(.34f,.83f,.39f);
        default: return FLinearColor(.30f,.95f,.79f);
    }
}
FLinearColor AGrowEvolutionWorld::ProfessionColor(EGrowProfession Value)
{
    return Value == EGrowProfession::Apprentice ? FLinearColor(.57f,.65f,.7f) :
        DecisionColor(Value == EGrowProfession::Caretaker ? EGrowDecision::Habitat : PrimaryFor(Value));
}
FVector AGrowEvolutionWorld::Station(EGrowDecision Decision)
{
    switch (Decision)
    {
        case EGrowDecision::Recycling: return FVector(-410,-280,0);
        case EGrowDecision::Water: return FVector(0,-475,0);
        case EGrowDecision::Logistics: return FVector(410,-250,0);
        case EGrowDecision::Energy: return FVector(-410,285,0);
        case EGrowDecision::Habitat: return FVector(405,285,0);
        default: return FVector(0,50,0);
    }
}

// Historical turns resolve with the same plan used by timed play. Rewinding never replays old timers.
void AGrowEvolutionWorld::Recompute()
{
    SystemLevels.Init(0,6);
    Profession = EGrowProfession::Apprentice;
    CreatureLevel = 0;
    EGrowProfession Context = EGrowProfession::Apprentice;
    TArray<EGrowDecision> Prefix;
    for (EGrowDecision Decision : History)
    {
        Prefix.Add(Decision);
        const int32 Selected = static_cast<int32>(Decision);
        SystemLevels[Selected] = 1;
        if (Decision == EGrowDecision::Awaken)
        {
            Profession = Context;
            CreatureLevel = 1;
        }
        else if (RoleFor(Decision) != EGrowProfession::Apprentice) Context = RoleFor(Decision);

        for(const auto& Upgrade:GrowRules::Plan(Prefix,SystemLevels,Profession))
            SystemLevels[static_cast<int32>(Upgrade.Target)]=Upgrade.Level;
        CreatureLevel=SystemLevels[static_cast<int32>(EGrowDecision::Awaken)];
    }
    RefreshInteractions();
}

bool AGrowEvolutionWorld::ChooseDecision(EGrowDecision Decision)
{
    if (!ValidDecision(Decision) || HasDecision(Decision) || History.Num() >= 6 || bResolving || TransitionRemaining > 0) return false;
    if(Decision==EGrowDecision::Awaken)
    {
        Profession=EGrowProfession::Apprentice;
        for(EGrowDecision Prior:History)if(RoleFor(Prior)!=EGrowProfession::Apprentice)Profession=RoleFor(Prior);
        CreatureLevel=1;
    }
    History.Add(Decision);
    SystemLevels[static_cast<int32>(Decision)]=1;
    if (Decision == EGrowDecision::Awaken)
        LastEvent = Profession == EGrowProfession::Apprentice ? TEXT("Despertaron sin un oficio que aprender. El contexto importa.") :
            FString::Printf(TEXT("Observaron %s y despertaron como %s."),*DecisionName(PrimaryFor(Profession)).ToLower(),*ProfessionName(Profession).ToLower());
    else LastEvent = DecisionName(Decision) + TEXT(" se incorpora a la red. Sus aportes habilitan nuevas mejoras.");
    TransitionRemaining = .45f;
    BuildUpgradePlan();
    RefreshInteractions();
    UpdateCreatures();
    return true;
}
bool AGrowEvolutionWorld::UndoDecision()
{
    if (History.IsEmpty()) return false;
    CancelUpgrades();
    UpgradeSerial=0;LastUpgrade=FGrowUpgrade();
    History.Pop();
    Recompute();
    TransitionRemaining = .45f;
    LastEvent = TEXT("Volviste una etapa. Probá una decisión diferente.");
    UpdateCreatures();
    return true;
}
void AGrowEvolutionWorld::ResetEvolution()
{
    CancelUpgrades();
    UpgradeSerial=0;LastUpgrade=FGrowUpgrade();
    History.Empty();
    Recompute();
    TransitionRemaining = .45f;
    LastEvent = TEXT("Nuevo comienzo. Lo que encuentren al despertar cambia su oficio.");
    UpdateCreatures();
}

void AGrowEvolutionWorld::CancelUpgrades()
{
    PendingUpgrades.Empty();PendingUpgradeCount=0;bResolving=false;
    EvolutionCountdown=0;TransitionRemaining=0;PendingReason.Empty();
}
void AGrowEvolutionWorld::BuildUpgradePlan()
{
    PendingUpgrades=GrowRules::Plan(History,SystemLevels,Profession);
    if(!PendingUpgrades.IsEmpty())StartNextUpgrade();
}
void AGrowEvolutionWorld::StartNextUpgrade()
{
    PendingUpgradeCount=PendingUpgrades.Num();
    bResolving=PendingUpgradeCount>0;
    if(!bResolving)
    {
        EvolutionCountdown=0;PendingReason.Empty();TransitionRemaining=.45f;
        return;
    }
    const auto& Upgrade=PendingUpgrades[0];
    PendingSource=Upgrade.Source;PendingDecision=Upgrade.Target;PendingReason=Upgrade.Reason;
    ActiveUpgradeDuration=FMath::Clamp(UpgradeDelaySeconds,.1f,10.f);
    EvolutionCountdown=ActiveUpgradeDuration;
    TransitionRemaining=EvolutionCountdown+(PendingUpgradeCount-1)*ActiveUpgradeDuration+.45f;
}
void AGrowEvolutionWorld::ApplyNextUpgrade()
{
    if(PendingUpgrades.IsEmpty()){CancelUpgrades();return;}
    const FGrowUpgrade Upgrade=PendingUpgrades[0];
    const int32 Index=static_cast<int32>(Upgrade.Target);
    if(SystemLevels[Index]+1!=Upgrade.Level||!GrowRules::Ready(Upgrade.Target,SystemLevels,Profession))
    {
        CancelUpgrades();
        LastEvent=TEXT("La red cambió. Elegí otra decisión para reorganizar sus aportes.");
        return;
    }
    SystemLevels[Index]=Upgrade.Level;
    CreatureLevel=SystemLevels[static_cast<int32>(EGrowDecision::Awaken)];
    LastUpgrade=Upgrade;++UpgradeSerial;LastEvent=Upgrade.Reason;
    PendingUpgrades.RemoveAt(0);
    RefreshInteractions();UpdateCreatures();StartNextUpgrade();
}
void AGrowEvolutionWorld::RefreshInteractions()
{
    Interactions.Reset();ActiveLinks=0;
    // Union of all professions keeps the visual graph stable while the colony discovers its role.
    for(int32 TargetIndex=0;TargetIndex<6;++TargetIndex)
    for(int32 Level=2;Level<=3;++Level)
    for(EGrowProfession RuleProfession:{EGrowProfession::Builder,EGrowProfession::Caretaker,EGrowProfession::Courier})
    for(const auto& Need:GrowRules::Requirements(static_cast<EGrowDecision>(TargetIndex),Level,RuleProfession))
    {
        auto* Existing=Interactions.FindByPredicate([&](const FGrowInteraction& Link)
            {return Link.Source==Need.Source&&static_cast<int32>(Link.Target)==TargetIndex;});
        if(Existing){Existing->RequiredLevel=FMath::Min(Existing->RequiredLevel,Need.Level);continue;}
        FGrowInteraction Link;Link.Source=Need.Source;Link.Target=static_cast<EGrowDecision>(TargetIndex);Link.RequiredLevel=Need.Level;
        Interactions.Add(Link);
    }
    for(auto& Link:Interactions)
    {
        Link.bActive=DecisionLevel(Link.Source)>=Link.RequiredLevel&&DecisionLevel(Link.Target)>0;
        if(Link.bActive)++ActiveLinks;
    }
}
FString AGrowEvolutionWorld::SystemHint(EGrowDecision Decision) const
{
    if(!ValidDecision(Decision))return TEXT("");
    if(!HasDecision(Decision))return DecisionDescription(Decision)+TEXT(". Al incorporarlo puede activar mejoras en los demás.");
    if(bResolving&&PendingDecision==Decision)return PendingReason;
    if(DecisionLevel(Decision)>=3)return TEXT("Nivel máximo. Sigue aportando a los otros sistemas de la red.");
    if(Decision==EGrowDecision::Awaken&&Profession==EGrowProfession::Apprentice)return TEXT("Necesitan un ejemplo ANTES de despertar. Deshacé para cambiar su contexto.");
    FString Missing;
    for(const auto& Need:GrowRules::Requirements(Decision,DecisionLevel(Decision)+1,Profession))
        if(DecisionLevel(Need.Source)<Need.Level)
            Missing+=(Missing.IsEmpty()?TEXT(""):TEXT(" + "))+GrowRules::Name(Need.Source)+FString::Printf(TEXT(" nivel %d"),Need.Level);
    if(!Missing.IsEmpty())return TEXT("Necesita ")+Missing+TEXT(".");
    return TEXT("Tiene los aportes necesarios. Puede crecer una vez por etapa; otra decisión abre la siguiente oportunidad.");
}
FString AGrowEvolutionWorld::PreviewProfession() const
{
    EGrowProfession Context = EGrowProfession::Apprentice;
    for (EGrowDecision Decision : History) if (RoleFor(Decision) != EGrowProfession::Apprentice) Context = RoleFor(Decision);
    return ProfessionName(CreatureLevel > 0 ? Profession : Context);
}
FString AGrowEvolutionWorld::ProgressHint() const
{
    if(bResolving)return PendingReason;
    if (CreatureLevel == 0) return TEXT("El último entre reciclaje, agua y transporte define qué aprenden al despertar.");
    if (Profession == EGrowProfession::Apprentice) return TEXT("Les faltó un ejemplo. Deshacé hasta antes de despertar y prepará un oficio.");
    if (CreatureLevel == 3) return TEXT("Oficio completo. Su obra final ya forma parte del mundo.");
    if(!GrowRules::Ready(EGrowDecision::Awaken,SystemLevels,Profession))return SystemHint(EGrowDecision::Awaken);
    if (IsComplete()) return TEXT("Les faltó tiempo para aprender. Probá despertarlos una etapa antes.");
    return TEXT("La próxima decisión iniciará otra reacción. Las mejoras llegan de una en una.");
}
FString AGrowEvolutionWorld::OutcomeText() const
{
    if (!IsComplete()) return TEXT("");
    if (!IsSuccessful()) return TEXT("Un mundo por descubrir. Cambiá el orden para completar su oficio.");
    switch (Profession)
    {
        case EGrowProfession::Builder: return TEXT("La cooperativa: construyeron un taller para toda la colonia.");
        case EGrowProfession::Caretaker: return TEXT("El jardín vivo: transformaron el patio en un refugio verde.");
        case EGrowProfession::Courier: return TEXT("La gran conexión: unieron el mundo con una red de reparto.");
        default: return TEXT("");
    }
}

void AGrowEvolutionWorld::BeginPlay()
{
    Super::BeginPlay();
    if (!BoxMesh) BoxMesh = LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (!CylinderMesh) CylinderMesh = LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    BuildPresentation();
    Recompute();
    BuildConnections();
    for (int32 Index=0; Index<3; ++Index)
    {
        auto* Creature = GetWorld()->SpawnActor<AGrowCreature>();
        if (Creature) { Creatures.Add(Creature); Creature->Configure(this,Index); }
    }
    UpdateCreatures();
}

void AGrowEvolutionWorld::AddPiece(const FString& Name, EGrowDecision Decision, int32 Level, FVector Position,
    FVector Scale, FLinearColor Color, bool bCylinder, float Spin, int32 RequiredCreatureLevel,
    EGrowProfession RequiredProfession, UStaticMesh* OverrideMesh)
{
    UStaticMeshComponent* Mesh = NewObject<UStaticMeshComponent>(this,*Name);
    Mesh->SetupAttachment(RootComponent);
    Mesh->SetStaticMesh(OverrideMesh ? OverrideMesh : bCylinder ? CylinderMesh.Get() : BoxMesh.Get());
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->SetCanEverAffectNavigation(false);
    Mesh->SetRelativeLocation(Position);
    Mesh->SetRelativeScale3D(Scale * .001f);
    if (DetailMaterial)
    {
        UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(DetailMaterial,this);
        Material->SetVectorParameterValue(TEXT("BaseColor"),Color);
        Material->SetScalarParameterValue(TEXT("Metallic"),.35f);
        Material->SetScalarParameterValue(TEXT("Roughness"),.42f);
        Material->SetVectorParameterValue(TEXT("Emission"),Color*(Name.Contains(TEXT("Light")) ? 1.5f : .02f));
        if (!OverrideMesh) Mesh->SetMaterial(0,Material);
    }
    Mesh->RegisterComponent();
    FGrowWorldPiece Piece;
    Piece.Mesh=Mesh; Piece.Decision=Decision; Piece.RequiredLevel=Level; Piece.Scale=Scale; Piece.Spin=Spin;
    Piece.RequiredCreatureLevel=RequiredCreatureLevel; Piece.RequiredProfession=RequiredProfession;
    Pieces.Add(Piece);
}

void AGrowEvolutionWorld::BuildPresentation()
{
    const FLinearColor Graphite(.052f,.082f,.105f), Steel(.26f,.34f,.37f), Ground(.17f,.23f,.25f), Soil(.12f,.075f,.045f);
    AddPiece(TEXT("IslandFoundation"),EGrowDecision::Awaken,0,FVector(0,0,-83),FVector(15.8f,15.8f,1.3f),Graphite,true);
    AddPiece(TEXT("IslandTop"),EGrowDecision::Awaken,0,FVector(0,0,-13),FVector(15.3f,15.3f,.15f),Ground,true);
    for (int32 Sector=0; Sector<6; ++Sector)
    {
        auto Decision=static_cast<EGrowDecision>(Sector);
        FVector P=Station(Decision);
        auto Color=DecisionColor(Decision);
        AddPiece(FString::Printf(TEXT("Socket_%d"),Sector),Decision,0,P+FVector(0,0,-1),FVector(3.2f,3.2f,.13f),Graphite,true);
        AddPiece(FString::Printf(TEXT("SocketLight_%d"),Sector),Decision,1,P+FVector(0,0,7),FVector(3.05f,3.05f,.08f),Color*.40f,true);
        AddPiece(FString::Printf(TEXT("SocketCap_%d"),Sector),Decision,1,P+FVector(0,0,12),FVector(2.85f,2.85f,.10f),Graphite,true);
        for (int32 Dot=0; Dot<3; ++Dot)
            AddPiece(FString::Printf(TEXT("LevelLight_%d_%d"),Sector,Dot),Decision,Dot+1,P+FVector(-50+Dot*50,128,22),FVector(.32f,.16f,.08f),Color);
    }
    // Central cradle. The same three creatures persist through all turns and rewinds.
    FVector Hub=Station(EGrowDecision::Awaken);
    AddPiece(TEXT("Cradle"),EGrowDecision::Awaken,0,Hub+FVector(0,0,13),FVector(2.25f,2.25f,.20f),Steel,true);
    for (int32 Index=0; Index<3; ++Index)
        AddPiece(FString::Printf(TEXT("CradleLight_%d"),Index),EGrowDecision::Awaken,1,Hub+FVector(-60+60*Index,0,29),FVector(.32f,.65f,.08f),DecisionColor(EGrowDecision::Awaken));

    FVector P=Station(EGrowDecision::Recycling); auto Orange=DecisionColor(EGrowDecision::Recycling);
    AddPiece(TEXT("RecyclerBase"),EGrowDecision::Recycling,1,P+FVector(0,0,47),FVector(1.65f,1.5f,.6f),Steel);
    for(int32 I=0;I<5;++I)
        AddPiece(FString::Printf(TEXT("Scrap_%d"),I),EGrowDecision::Recycling,1,P+FVector(-50+I*23,15,85+(I%2)*9),FVector(.30f,.70f,.15f),I%2?Orange:Steel);
    for(int32 I : {-1,1})
        AddPiece(FString::Printf(TEXT("PressPillar_%d"),I),EGrowDecision::Recycling,2,P+FVector(I*70,-45,135),FVector(.20f,.25f,1.85f),Orange);
    AddPiece(TEXT("PressHead"),EGrowDecision::Recycling,2,P+FVector(0,-45,185),FVector(1.65f,.72f,.28f),Graphite);
    AddPiece(TEXT("RecyclerRotor"),EGrowDecision::Recycling,3,P+FVector(0,20,122),FVector(.95f,.28f,.22f),Orange,false,100);

    P=Station(EGrowDecision::Water); auto Blue=DecisionColor(EGrowDecision::Water);
    AddPiece(TEXT("WaterTank"),EGrowDecision::Water,1,P+FVector(0,0,49),FVector(1.9f,1.9f,.62f),Steel,true);
    AddPiece(TEXT("WaterLight"),EGrowDecision::Water,1,P+FVector(0,0,81),FVector(1.65f,1.65f,.045f),Blue,true);
    AddPiece(TEXT("Pump"),EGrowDecision::Water,2,P+FVector(-75,0,115),FVector(.45f,.45f,.9f),Blue,true);
    for(int32 I=0;I<5;++I)
        AddPiece(FString::Printf(TEXT("WaterPipe_%d"),I),EGrowDecision::Water,2,P+FVector(80+I*52,85+I*86,20),FVector(.27f,.85f,.25f),Blue*.5f);
    for(int32 I=0;I<3;++I)
        AddPiece(FString::Printf(TEXT("FountainLight_%d"),I),EGrowDecision::Water,3,P+FVector(-40+I*40,0,125+I*18),FVector(.12f,.12f,.48f),Blue,true,45);

    P=Station(EGrowDecision::Energy); auto Yellow=DecisionColor(EGrowDecision::Energy);
    AddPiece(TEXT("Generator"),EGrowDecision::Energy,1,P+FVector(0,0,60),FVector(1.3f,1.3f,.85f),Steel,true);
    AddPiece(TEXT("GeneratorLight"),EGrowDecision::Energy,1,P+FVector(0,0,110),FVector(1.05f,1.05f,.18f),Yellow,true);
    AddPiece(TEXT("TurbineMast"),EGrowDecision::Energy,2,P+FVector(0,0,180),FVector(.23f,.23f,1.6f),Steel,true);
    AddPiece(TEXT("TurbineA"),EGrowDecision::Energy,2,P+FVector(0,0,267),FVector(2.6f,.22f,.10f),Yellow,false,65);
    AddPiece(TEXT("TurbineB"),EGrowDecision::Energy,2,P+FVector(0,0,267),FVector(.22f,2.6f,.10f),Yellow,false,65);
    for(int32 I=0;I<4;++I)
        AddPiece(FString::Printf(TEXT("Battery_%d"),I),EGrowDecision::Energy,3,P+FVector(-90+I*60,80,48),FVector(.3f,.35f,.55f),Yellow*.55f);

    P=Station(EGrowDecision::Logistics); auto Violet=DecisionColor(EGrowDecision::Logistics);
    for(int32 I=0;I<3;++I)
    {
        AddPiece(FString::Printf(TEXT("Conveyor_%d"),I),EGrowDecision::Logistics,I+1,P+FVector(-150+I*120,0,22),BeltMesh?FVector(.6f,.68f,.65f):FVector(1.2f,1,.25f),Graphite,false,0,0,EGrowProfession::Apprentice,BeltMesh);
        for(int32 Slat=0;Slat<8;++Slat)
            AddPiece(FString::Printf(TEXT("BeltSlat_%d_%d"),I,Slat),EGrowDecision::Logistics,I+1,P+FVector(-198+I*120+Slat*14,0,44),FVector(.06f,.82f,.045f),Steel*.5f);
        AddPiece(FString::Printf(TEXT("Parcel_%d"),I),EGrowDecision::Logistics,I+1,P+FVector(-110+I*110,0,66),FVector(.32f,.32f,.35f),Violet);
    }

    P=Station(EGrowDecision::Habitat); auto Green=DecisionColor(EGrowDecision::Habitat);
    for(int32 I=0;I<3;++I)
    {
        const FVector Bed=P+FVector(-88+I*80,0,20);
        AddPiece(FString::Printf(TEXT("Planter_%d"),I),EGrowDecision::Habitat,I+1,Bed+FVector(0,0,8),FVector(.70f,1.45f,.2f),Steel);
        AddPiece(FString::Printf(TEXT("Soil_%d"),I),EGrowDecision::Habitat,I+1,Bed+FVector(0,0,20),FVector(.61f,1.31f,.08f),Soil);
        for(int32 J=0;J<3;++J)
        {
            AddPiece(FString::Printf(TEXT("SproutStem_%d_%d"),I,J),EGrowDecision::Habitat,I+1,Bed+FVector(0,-42+J*42,45+I*12),FVector(.08f,.08f,.4f+I*.15f),Green*.45f,true);
            AddPiece(FString::Printf(TEXT("SproutLeaf_%d_%d"),I,J),EGrowDecision::Habitat,I+1,Bed+FVector(0,-42+J*42,70+I*19),FVector(.40f,.22f,.15f),Green,false,6);
        }
    }
    // Profession-specific landmarks appear through the colony's work, not simply from selecting the system.
    P=FVector(-185,-110,0);
    for(int32 I : {-1,1})
        AddPiece(FString::Printf(TEXT("WorkshopPost_%d"),I),EGrowDecision::Awaken,1,P+FVector(I*95,0,90),FVector(.24f,1.45f,1.65f),Steel,false,0,3,EGrowProfession::Builder);
    AddPiece(TEXT("WorkshopRoof"),EGrowDecision::Awaken,1,P+FVector(0,0,180),FVector(2.35f,1.9f,.2f),Orange,false,0,3,EGrowProfession::Builder);
    AddPiece(TEXT("WorkshopBench"),EGrowDecision::Awaken,1,P+FVector(0,0,65),FVector(1.5f,.55f,.15f),Orange,false,0,2,EGrowProfession::Builder);
    P=FVector(235,70,0);
    AddPiece(TEXT("GardenTrunk"),EGrowDecision::Awaken,1,P+FVector(0,0,90),FVector(.3f,.3f,1.7f),Soil,true,0,2,EGrowProfession::Caretaker);
    for(int32 I=0;I<3;++I)
        AddPiece(FString::Printf(TEXT("GardenCanopy_%d"),I),EGrowDecision::Awaken,1,P+FVector(0,0,160+I*48),FVector(1.55f-I*.35f,1.55f-I*.35f,.57f),Green*(.6f+I*.18f),true,0,3,EGrowProfession::Caretaker);
    P=FVector(190,-80,0);
    AddPiece(TEXT("Depot"),EGrowDecision::Awaken,1,P+FVector(0,0,55),FVector(1.2f,1.2f,.85f),Steel,false,0,2,EGrowProfession::Courier);
    AddPiece(TEXT("DepotLight"),EGrowDecision::Awaken,1,P+FVector(0,0,107),FVector(1.5f,1.5f,.18f),Violet,false,0,3,EGrowProfession::Courier);
    for(int32 I=0;I<8;++I)
        AddPiece(FString::Printf(TEXT("DeliveryRoad_%d"),I),EGrowDecision::Awaken,1,FVector(-260+I*70,120,8),FVector(.56f,.42f,.08f),Violet*.7f,false,0,3,EGrowProfession::Courier);
}

void AGrowEvolutionWorld::UpdateCreatures()
{
    for (AGrowCreature* Creature : Creatures) if (IsValid(Creature)) Creature->ApplyEvolution();
}
void AGrowEvolutionWorld::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(bResolving)
    {
        EvolutionCountdown=FMath::Max(0.f,EvolutionCountdown-DeltaSeconds);
        if(EvolutionCountdown<=0)ApplyNextUpgrade();
        else TransitionRemaining=EvolutionCountdown+(PendingUpgradeCount-1)*ActiveUpgradeDuration+.45f;
    }
    else TransitionRemaining=FMath::Max(0.f,TransitionRemaining-DeltaSeconds);
    MotionPhase+=DeltaSeconds;
    UpdateConnections(DeltaSeconds);
    VisiblePieceCount=0;
    for (auto& Piece : Pieces)
    {
        if (!Piece.Mesh) continue;
        const bool bVisible=(Piece.RequiredLevel==0 || DecisionLevel(Piece.Decision)>=Piece.RequiredLevel) &&
            (Piece.RequiredCreatureLevel==0 || (CreatureLevel>=Piece.RequiredCreatureLevel && Profession==Piece.RequiredProfession));
        Piece.Reveal=FMath::FInterpConstantTo(Piece.Reveal,bVisible?1.f:0.f,DeltaSeconds,2.6f);
        Piece.Mesh->SetVisibility(Piece.Reveal>.005f);
        const float T=FMath::SmoothStep(0.f,1.f,Piece.Reveal);
        Piece.Mesh->SetRelativeScale3D(Piece.Scale*FVector(FMath::Max(T,.001f),FMath::Max(T,.001f),FMath::Max(T,.001f)));
        if (bVisible) ++VisiblePieceCount;
        if (Piece.Spin!=0) Piece.Mesh->SetRelativeRotation(Piece.Rotation+FRotator(0,MotionPhase*Piece.Spin,0));
        const FString Name=Piece.Mesh->GetName();
        if(Name==TEXT("PressHead")) Piece.Mesh->SetRelativeLocation(Station(EGrowDecision::Recycling)+FVector(0,-45,185+FMath::Sin(MotionPhase*3)*15));
        if(Name.StartsWith(TEXT("Parcel_")))
        {
            const int32 Index=FCString::Atoi(*Name.Right(1));
            const float RunLength=FMath::Max(40.f,DecisionLevel(EGrowDecision::Logistics)*120.f-32.f);
            Piece.Mesh->SetRelativeLocation(Station(EGrowDecision::Logistics)+FVector(-195+FMath::Fmod(MotionPhase*45+Index*95,RunLength),0,66));
        }
    }
}

AGrowCreature::AGrowCreature()
{
    PrimaryActorTick.bCanEverTick=true;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("CreatureRoot"));
    Body=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("CreatureBody"));
    Body->SetupAttachment(RootComponent);
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Body->SetCanEverAffectNavigation(false);
    Body->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Accessory=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ProfessionAccessory"));
    Accessory->SetupAttachment(RootComponent);
    Accessory->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Accessory->SetCanEverAffectNavigation(false);
    Cargo=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WorkCargo"));
    Cargo->SetupAttachment(RootComponent);
    Cargo->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Cargo->SetCanEverAffectNavigation(false);
}
void AGrowCreature::Configure(AGrowEvolutionWorld* InWorld,int32 Index)
{
    Evolution=InWorld; ColonyIndex=Index; Species=InWorld->Species;
    MotionPhase=Index*2.1f;
    if(Species)
    {
        Body->SetSkeletalMesh(Species->BodyMesh);
        Body->SetRelativeRotation(Species->BodyRotation);
        Body->SetRelativeScale3D(Species->BodyScale);
        Accessory->SetRelativeLocation(Species->AccessoryOffset);
        Accessory->SetRelativeScale3D(Species->BodyScale);
        Body->PlayAnimation(Species->IdleAnimation,true);
    }
    Cargo->SetStaticMesh(InWorld->BoxMesh);
    Cargo->SetRelativeLocation(FVector(35,0,55));
    Cargo->SetRelativeScale3D(FVector(.27f,.40f,.25f));
    ApplyEvolution();
}
void AGrowCreature::ApplyEvolution()
{
    if(!Evolution)return;
    const int32 PreviousLevel=Level;
    Profession=Evolution->Profession; Level=Evolution->CreatureLevel;
    SetActorHiddenInGame(Level==0);
    if(Level==0||PreviousLevel==0)
    {
        JobStage=0;WorkPause=ColonyIndex*.35f;bDelivering=false;CompletedTrips=0;
        SetActorLocation(AGrowEvolutionWorld::Station(EGrowDecision::Awaken)+FVector(-60+60*ColonyIndex,0,18));
    }
    if(JobStage>0 && (!Evolution->HasDecision(WorkSource)||!Evolution->HasDecision(WorkTarget)))
        {JobStage=0;bDelivering=false;WorkPause=0;}
    Accessory->SetStaticMesh(Species?Species->ProfessionMeshes.FindRef(Profession):nullptr);
    Cargo->SetVisibility(bDelivering);
    if(Evolution->DetailMaterial)
    {
        auto* Material=UMaterialInstanceDynamic::Create(Evolution->DetailMaterial,this);
        Material->SetVectorParameterValue(TEXT("BaseColor"),AGrowEvolutionWorld::ProfessionColor(Profession));
        Material->SetVectorParameterValue(TEXT("Emission"),AGrowEvolutionWorld::ProfessionColor(Profession)*.08f);
        Cargo->SetMaterial(0,Material);
    }
    Activity=Level==0?TEXT("En espera"):Profession==EGrowProfession::Apprentice?TEXT("Observando"):
        Profession==EGrowProfession::Builder?TEXT("Construyendo"):Profession==EGrowProfession::Caretaker?TEXT("Cuidando brotes"):TEXT("Repartiendo");
}
void AGrowCreature::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!Evolution || Level==0 || !Species)return;
    MotionPhase+=DeltaSeconds;
    WorkPause=FMath::Max(0.f,WorkPause-DeltaSeconds);
    auto GoalFor=[&](EGrowDecision Node,EGrowDecision Other)
    {
        const FVector Center=AGrowEvolutionWorld::Station(Node);
        const FVector Direction=(AGrowEvolutionWorld::Station(Other)-Center).GetSafeNormal2D();
        const FVector Lane(-Direction.Y,Direction.X,0);
        return Center+Direction*165.f+Lane*((ColonyIndex-1)*54.f)+FVector(0,0,18);
    };
    if(JobStage==0&&WorkPause<=0)
    {
        WorkSource=Profession==EGrowProfession::Apprentice?EGrowDecision::Awaken:PrimaryFor(Profession);
        WorkTarget=Profession==EGrowProfession::Apprentice?EGrowDecision::Awaken:SupportFor(Profession);
        if(Evolution->bResolving){WorkSource=Evolution->PendingSource;WorkTarget=Evolution->PendingDecision;}
        if(!Evolution->HasDecision(WorkTarget))WorkTarget=EGrowDecision::Awaken;
        if(!Evolution->HasDecision(WorkSource))WorkSource=EGrowDecision::Awaken;
        if(WorkSource!=WorkTarget)
        {
            JobStage=1;WorkGoal=GoalFor(WorkSource,WorkTarget);
            Activity=TEXT("Recogiendo aportes de ")+GrowRules::Name(WorkSource);
        }
        else
        {
            WorkGoal=AGrowEvolutionWorld::Station(EGrowDecision::Awaken)+FVector(-95+95*ColonyIndex,90,18);
            Activity=TEXT("Observando la red");
        }
    }
    const FVector Current=GetActorLocation();
    const FVector Direction=WorkGoal-Current;
    const bool bMove=WorkPause<=0&&Direction.Size2D()>3;
    if(bMove)
    {
        const float Speed=95.f+Level*20.f+(Profession==EGrowProfession::Courier?35.f:0.f);
        SetActorLocation(FMath::VInterpConstantTo(Current,WorkGoal,DeltaSeconds,Speed));
        SetActorRotation(FMath::RInterpTo(GetActorRotation(),Direction.Rotation(),DeltaSeconds,9));
    }
    else if(WorkPause<=0)
    {
        if(JobStage==1)
        {
            WorkPause=.5f;JobStage=2;bDelivering=true;
            WorkGoal=GoalFor(WorkTarget,WorkSource);
            Activity=TEXT("Llevando ")+GrowRules::Contribution(WorkSource,WorkTarget)+TEXT(" a ")+GrowRules::Name(WorkTarget);
        }
        else if(JobStage==2)
        {
            ++CompletedTrips;JobStage=0;WorkPause=.8f;bDelivering=false;
            Activity=TEXT("Colaborando en ")+GrowRules::Name(WorkTarget);
        }
    }
    Cargo->SetVisibility(bDelivering);
    if(bMove!=bWalking)
    {
        bWalking=bMove;
        Body->PlayAnimation(bWalking?Species->WalkAnimation:Species->IdleAnimation,true);
    }
    if(!bMove) Body->SetRelativeRotation(Species->BodyRotation+FRotator(FMath::Sin(MotionPhase*5)*4,0,0));
    else Body->SetRelativeRotation(Species->BodyRotation);
    Accessory->SetRelativeLocation(Species->AccessoryOffset+FVector(0,0,FMath::Sin(MotionPhase*5)*1.2f));
}

AGrowViewPawn::AGrowViewPawn()
{
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("ViewRoot"));
    SpringArm=CreateDefaultSubobject<USpringArmComponent>(TEXT("SpringArm"));
    SpringArm->SetupAttachment(RootComponent);
    SpringArm->TargetArmLength=4500;
    SpringArm->TargetOffset=FVector(240,240,-260);
    SpringArm->SetRelativeRotation(FRotator(-52,-45,0));
    SpringArm->bDoCollisionTest=false;
    Camera=CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
    Camera->SetupAttachment(SpringArm,USpringArmComponent::SocketName);
    Camera->FieldOfView=40;
    CameraControls=CreateDefaultSubobject<UFactoryCameraComponent>(TEXT("CameraControls"));
    CameraControls->MinimumDistance=1700;
    CameraControls->MaximumDistance=6500;
}
AGrowEvolutionWorld* AGrowPlayerController::Evolution() const
{
    if(GetWorld())for(TActorIterator<AGrowEvolutionWorld> It(GetWorld());It;++It)return *It;
    return nullptr;
}
void AGrowPlayerController::BeginPlay()
{
    Super::BeginPlay();
    bShowMouseCursor=true;
    FInputModeGameAndUI Mode;
    Mode.SetHideCursorDuringCapture(false);
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    SetInputMode(Mode);
}
void AGrowPlayerController::SetupInputComponent()
{
    Super::SetupInputComponent();
    InputComponent->BindKey(EKeys::One,IE_Pressed,this,&AGrowPlayerController::Choose0);
    InputComponent->BindKey(EKeys::Two,IE_Pressed,this,&AGrowPlayerController::Choose1);
    InputComponent->BindKey(EKeys::Three,IE_Pressed,this,&AGrowPlayerController::Choose2);
    InputComponent->BindKey(EKeys::Four,IE_Pressed,this,&AGrowPlayerController::Choose3);
    InputComponent->BindKey(EKeys::Five,IE_Pressed,this,&AGrowPlayerController::Choose4);
    InputComponent->BindKey(EKeys::Six,IE_Pressed,this,&AGrowPlayerController::Choose5);
    InputComponent->BindKey(EKeys::BackSpace,IE_Pressed,this,&AGrowPlayerController::Undo);
    InputComponent->BindKey(EKeys::R,IE_Pressed,this,&AGrowPlayerController::Restart);
    InputComponent->BindKey(EKeys::LeftMouseButton,IE_Pressed,this,&AGrowPlayerController::Click);
}
void AGrowPlayerController::Choose0(){if(auto* W=Evolution())W->ChooseDecision(EGrowDecision::Recycling);}
void AGrowPlayerController::Choose1(){if(auto* W=Evolution())W->ChooseDecision(EGrowDecision::Water);}
void AGrowPlayerController::Choose2(){if(auto* W=Evolution())W->ChooseDecision(EGrowDecision::Logistics);}
void AGrowPlayerController::Choose3(){if(auto* W=Evolution())W->ChooseDecision(EGrowDecision::Energy);}
void AGrowPlayerController::Choose4(){if(auto* W=Evolution())W->ChooseDecision(EGrowDecision::Habitat);}
void AGrowPlayerController::Choose5(){if(auto* W=Evolution())W->ChooseDecision(EGrowDecision::Awaken);}
void AGrowPlayerController::Undo(){if(auto* W=Evolution())W->UndoDecision();}
void AGrowPlayerController::Restart(){if(auto* W=Evolution())W->ResetEvolution();}
void AGrowPlayerController::Click()
{
    float X,Y;
    if(GetMousePosition(X,Y))if(auto* HUD=Cast<AGrowEvolutionHUD>(GetHUD()))HUD->Click(X,Y);
}
AGrowEvolutionGameMode::AGrowEvolutionGameMode()
{
    DefaultPawnClass=AGrowViewPawn::StaticClass();
    PlayerControllerClass=AGrowPlayerController::StaticClass();
    HUDClass=AGrowEvolutionHUD::StaticClass();
}
