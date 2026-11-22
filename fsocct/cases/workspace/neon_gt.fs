FeatureScript 2892;
import(path : "onshape/std/common.fs", version : "2892.0");

// NEON GT R1. Millimetres. Front +X, left +Y, roof +Z.
// Body prints underside down. Wheels print inner face down. Two axles print flat.
function poly(context is Context,id is Id,origin is Vector,n is Vector,x is Vector,pts is array) returns Query
{
 var s=newSketchOnPlane(context,id,{"sketchPlane":plane(origin*millimeter,n,x)});var pp=[];
 for(var p in pts)pp=append(pp,vector(p[0],p[1])*millimeter);
 pp=append(pp,pp[0]);skPolyline(s,"outline",{"points":pp});skSolve(s);return qSketchRegion(id,true);
}
function prism(context is Context,id is Id,origin is Vector,n is Vector,x is Vector,pts is array,h is number) returns Query
{
 var q=poly(context,id+"sk",origin,n,x,pts);
 opExtrude(context,id+"ex",{"entities":q,"direction":n,"endBound":BoundingType.BLIND,"endDepth":h*millimeter});
 opDeleteBodies(context,id+"ds",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});return qCreatedBy(id+"ex",EntityType.BODY);
}
function makeBox(context is Context,id is Id,a is Vector,b is Vector) returns Query
{return prism(context,id,vector(0,0,a[2]),vector(0,0,1),vector(1,0,0),[[a[0],a[1]],[b[0],a[1]],[b[0],b[1]],[a[0],b[1]]],b[2]-a[2]);}
function cyl(context is Context,id is Id,o is Vector,n is Vector,r is number,h is number) returns Query
{
 var s=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(o*millimeter,n,vector(1,0,0))});
 skCircle(s,"c",{"center":vector(0,0)*millimeter,"radius":r*millimeter});skSolve(s);
 opExtrude(context,id+"ex",{"entities":qSketchRegion(id+"sk",true),"direction":n,"endBound":BoundingType.BLIND,"endDepth":h*millimeter});
 opDeleteBodies(context,id+"ds",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});return qCreatedBy(id+"ex",EntityType.BODY);
}
function cut(context is Context,id is Id,b is Query,t is Query)
{opBoolean(context,id,{"targets":b,"tools":t,"operationType":BooleanOperationType.SUBTRACTION});}
function join(context is Context,id is Id,qs is array) returns Query
{opBoolean(context,id,{"tools":qUnion(qs),"operationType":BooleanOperationType.UNION});return qBodyType(qUnion(append(qs,qCreatedBy(id,EntityType.BODY))),BodyType.SOLID);}
function paint(context is Context,b is Query,c)
{if(size(evaluateQuery(context,b))==0){println("Appearance query empty: "~b);return;}setProperty(context,{"entities":b,"propertyType":PropertyType.APPEARANCE,"value":c});}
function finish(context is Context,b is Query,name is string,c)
{
 if(size(evaluateQuery(context,b))!=1)throw regenError("Expected one solid: "~name);
 setProperty(context,{"entities":b,"propertyType":PropertyType.NAME,"value":name});paint(context,b,c);
}
function body(context is Context,id is Id) returns Query
{
 var outline=[[-60,-18],[-54,-25],[-33,-27],[-16,-23],[15,-23],[35,-27],[54,-23],[62,-16],[62,16],[54,23],[35,27],[15,23],[-16,23],[-33,27],[-54,25],[-60,18]];
 var base=prism(context,id+"base",vector(0,0,0),vector(0,0,1),vector(1,0,0),outline,23);
 // Chamfered lower body / sculpted wedge nose.
 var nose=prism(context,id+"nose",vector(0,40,0),vector(0,-1,0),vector(1,0,0),[[47,23],[64,11],[68,11],[68,45],[47,45]],80);
 cut(context,id+"noseCut",base,nose);
 var tail=prism(context,id+"tail",vector(0,40,0),vector(0,-1,0),vector(1,0,0),[[-64,15],[-52,23],[-52,45],[-64,45]],80);
 cut(context,id+"tailCut",base,tail);
 var cabin=prism(context,id+"cabin",vector(0,17,0),vector(0,-1,0),vector(1,0,0),[[-31,22],[-17,36],[8,36],[30,22]],34);
 base=join(context,id+"cabinJoin",[base,cabin]);
 // Taper the greenhouse sides; local X=Y, local Y=Z.
 for(var side in [-1,1])
 {
  var t=prism(context,id+("taper"~side),vector(-45,0,0),vector(1,0,0),vector(0,1,0),side==1 ? [[17,23],[11.8,38],[35,38],[35,23]] : [[-17,23],[-11.8,38],[-35,38],[-35,23]],90);
  cut(context,id+("taperCut"~side),base,t);
 }
 // Gentle rounding before detail cuts keeps printed edges comfortable.
 opFillet(context,id+"softEdges",{"entities":qOwnedByBody(base,EntityType.EDGE),"radius":.65*millimeter,"tangentPropagation":false});
 // Wheel wells remain closed above: 2.8 mm nominal crown at each axle.
 for(var ax in [-36,36])
 {
  for(var side in [-1,1])
  {
   var t=cyl(context,id+("arch"~ax~"_"~side),vector(ax,side*17.5,7),vector(0,side,0),13.2,20);
   cut(context,id+("archCut"~ax~"_"~side),base,t);
  }
  var t=cyl(context,id+("bearing"~ax),vector(ax,-30,7),vector(0,1,0),2.3,60);
  cut(context,id+("bearingCut"~ax),base,t);
 }
 // Open underside weight relief with a 45 degree tent ceiling.
 var pocket=prism(context,id+"pocket",vector(-23,0,0),vector(1,0,0),vector(0,1,0),[[-16,-1],[16,-1],[16,1],[0,17],[-16,1]],46);
 cut(context,id+"pocketCut",base,pocket);
 // Side windows recessed into tapered greenhouse. The sloped cutting planes
 // follow the actual body taper so their depth is controlled.
 var slope=5.2/15;var nn=normalize(vector(0,1,slope));
 for(var side in [-1,1])
 {
  var n=vector(0,-side*nn[1],-nn[2]);
  var t=prism(context,id+("window"~side),vector(0,side*17.15,23),n,vector(1,0,0),side==1 ? [[-26,1],[-15,12],[6,12],[24,1]] : [[-26,-1],[-15,-12],[6,-12],[24,-1]],1.25);
  cut(context,id+("windowCut"~side),base,t);
 }
 // Windshield pocket lies on the front sloped roof plane.
 var windN=normalize(vector(-14,0,-22));
 var wind=prism(context,id+"wind",vector(29.4,0,22.6),windN,vector(0,-1,0),[[-14,2],[14,2],[10.8,21],[-10.8,21]],1.1);
 cut(context,id+"windCut",base,wind);
 // Recessed hood lines, blade lamps, rear grille, side intake and roof stripes.
 for(var side in [-1,1])
 {
  var vent=makeBox(context,id+("sideVent"~side),vector(-13,side==1?21.3:-30,8),vector(11,side==1?30:-21.3,14));
  cut(context,id+("sideVentCut"~side),base,vent);
  var lamp=makeBox(context,id+("lamp"~side),vector(58,side==1?7:-18,9),vector(65,side==1?18:-7,10.7));
  cut(context,id+("lampCut"~side),base,lamp);
 }
 for(var x in [-46,-42,-38,-34])
 {
  var vent=makeBox(context,id+("deckVent"~x),vector(x,-12,22.1),vector(x+1.8,12,25));
  cut(context,id+("deckVentCut"~x),base,vent);
 }
 // Twin raised racing stripes create real paintable detail.
 for(var y in [-3.9,2.1])
 {
  var stripe=makeBox(context,id+("stripe"~y),vector(-13,y,35.6),vector(5,y+1.8,36.6));
  base=join(context,id+("stripeJoin"~y),[base,stripe]);
 }
 // Integrated ducktail spoiler: solid ramp, no fragile separate stanchions.
 var wing=prism(context,id+"wing",vector(0,25,0),vector(0,-1,0),vector(1,0,0),[[-59,18],[-50,22],[-53,28],[-60,28]],50);
 base=join(context,id+"wingJoin",[base,wing]);
 finish(context,base,"NEON GT / monocoque R1",color(.08,.82,.68));
 var glass=[];var vents=[];var lights=[];
 for(var f in evaluateQuery(context,qOwnedByBody(base,EntityType.FACE)))
 {
  var surf=evSurfaceDefinition(context,{"face":f});
  if(!(surf is Plane))continue;
  var o=surf.origin/millimeter;var n=surf.normal;var bb=evBox3d(context,{"topology":f,"tight":true});var p=(bb.minCorner+bb.maxCorner)/(2*millimeter);
  if(abs(n[1])>.8 && abs(n[2])>.2 && abs(n[2])<.5 && p[2]>25 && abs(o[1])+slope*o[2]<24.5 && abs(o[1])+slope*o[2]>22)glass=append(glass,f);
  if(abs(n[0])>.4 && abs(n[0])<.65 && abs(n[2])>.7 && p[0]>8 && p[2]>23 && 14*o[0]+22*o[2]<895 && 14*o[0]+22*o[2]>865)glass=append(glass,f);
  if(abs(n[1])>.99 && abs(p[1])>21 && abs(p[1])<21.5 && p[2]>9 && p[2]<13 && p[0]>-14 && p[0]<12)vents=append(vents,f);
  if(abs(n[2])>.99 && abs(p[2]-22.1)<.01 && p[0]<-30)vents=append(vents,f);
  if(abs(n[0])>.99 && abs(p[0]-58)<.01 && p[2]>8.9 && p[2]<10.8)lights=append(lights,f);
 }
 if(size(glass)!=3)throw regenError("Expected three recessed glass faces, found "~size(glass));
 paint(context,qUnion(glass),color(.025,.055,.08));
 paint(context,qUnion(vents),color(.045,.065,.08));
 paint(context,qUnion(lights),color(.98,.94,.68));
 for(var y in [-3.9,2.1])paint(context,qCreatedBy(id+("stripe"~y)+"ex",EntityType.FACE),color(.04,.07,.09));
 return base;
}
function wheel(context is Context,id is Id) returns Query
{
 var w=cyl(context,id+"tire",vector(0,0,0),vector(0,0,1),12,8);
 opFillet(context,id+"round",{"entities":qOwnedByBody(w,EntityType.EDGE),"radius":.8*millimeter});
 var rim=cyl(context,id+"rim",vector(0,0,7.6),vector(0,0,1),8.7,1.0);
 w=join(context,id+"rimJoin",[w,rim]);
 for(var i=0;i<5;i+=1)
 {
  var a=i*72*degree;var pts=[];
  for(var p in [[4.2,-.7],[7.4,-1.3],[7.4,1.3],[5.1,1.6]])pts=append(pts,[p[0]*cos(a)-p[1]*sin(a),p[0]*sin(a)+p[1]*cos(a)]);
  var t=prism(context,id+("spoke"~i),vector(0,0,7.2),vector(0,0,1),vector(1,0,0),pts,2);
  cut(context,id+("spokeCut"~i),w,t);
 }
 var bore=cyl(context,id+"bore",vector(0,0,-1),vector(0,0,1),2.1,11);cut(context,id+"boreCut",w,bore);
 finish(context,w,"NEON GT / wheel",color(.065,.075,.085));
 paint(context,qCreatedBy(id+"rim"+"ex",EntityType.FACE),color(.68,.74,.79));
 return w;
}
function axle(context is Context,id is Id) returns Query
{
 // A D-section lies flat and remains within a 4 mm turning envelope.
 var a=cyl(context,id+"shaft",vector(0,0,0),vector(0,0,1),2,51.8);
 var t=makeBox(context,id+"flat",vector(-3,-3,-1),vector(3,-1.5,53));cut(context,id+"flatCut",a,t);
 finish(context,a,"NEON GT / axle 4 x 51.8",color(.95,.40,.08));return a;
}
function build(context is Context,id is Id,layout is boolean)
{
 body(context,id+"body");var i=0;
 for(var x in [-36,36])for(var side in [-1,1])
 {
  var w=wheel(context,id+("wheel"~i));
  var tr=layout ? transform(vector(-44+i*29,-49,0)*millimeter) : toWorld(coordSystem(vector(x,side*18.2,7)*millimeter,vector(1,0,0),vector(0,side,0)));
  opTransform(context,id+("wheelPose"~i),{"bodies":w,"transform":tr});i+=1;
 }
 i=0;
 for(var x in [-36,36])
 {
  var a=axle(context,id+("axle"~i));
  var tr=layout ? toWorld(coordSystem(vector(-26,-70-i*7,1.5)*millimeter,vector(0,1,0),vector(1,0,0))) : toWorld(coordSystem(vector(x,-25.9,7)*millimeter,vector(1,0,0),vector(0,1,0)));
  opTransform(context,id+("axlePose"~i),{"bodies":a,"transform":tr});i+=1;
 }
 if(size(evaluateQuery(context,qAllModifiableSolidBodies()))!=7)throw regenError("NEON GT must contain seven printable solids");
}
annotation {"Feature Type Name":"NEON GT - assembled"}
export const neonGT=defineFeature(function(context is Context,id is Id,definition is map)
precondition {} {build(context,id,false);});
annotation {"Feature Type Name":"NEON GT - print layout"}
export const neonGTPrint=defineFeature(function(context is Context,id is Id,definition is map)
precondition {} {build(context,id,true);});
