FeatureScript 3070;
import(path : "onshape/std/common.fs", version : "3070.0");

// Halloween Lochwand R1. Millimetres. Board coordinates: +X right, +Y rear, +Z up.
// The board is tilted 8 degrees backwards after construction. Materials and fits
// are assumptions. A native concept, not cutting data or a physical validation.
function lwOne(context is Context, query is Query) returns Query
{
    var q = qBodyType(query, BodyType.SOLID);
    if (size(evaluateQuery(context, q)) != 1) throw regenError("Expected one connected part");
    return q;
}
function lwPrism(context is Context, id is Id, pl is Plane, pts is array, depth) returns Query
{
    var sk = newSketchOnPlane(context, id + "sk", {"sketchPlane" : pl});
    for (var i = 0; i < size(pts); i += 1)
        skLineSegment(sk, "e" ~ i, {"start" : vector(pts[i][0], pts[i][1]) * millimeter,
            "end" : vector(pts[(i + 1) % size(pts)][0], pts[(i + 1) % size(pts)][1]) * millimeter});
    skSolve(sk);
    opExtrude(context, id + "ex", {"entities" : qSketchRegion(id + "sk", false), "direction" : pl.normal,
        "endBound" : BoundingType.BLIND, "endDepth" : depth * millimeter});
    opDeleteBodies(context, id + "clean", {"entities" : qCreatedBy(id + "sk", EntityType.BODY)});
    return lwOne(context, qCreatedBy(id + "ex", EntityType.BODY));
}
function lwBox(context is Context, id is Id, x0,y0,z0,x1,y1,z1) returns Query
{
    return lwPrism(context,id,plane(vector(0,0,z0)*millimeter,vector(0,0,1),vector(1,0,0)),
        [[x0,y0],[x1,y0],[x1,y1],[x0,y1]],z1-z0);
}
function lwCylinder(context is Context, id is Id, p is Vector, axis is Vector, r, h) returns Query
{
    var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(p*millimeter,axis)});
    skCircle(sk,"circle",{"center":vector(0,0)*millimeter,"radius":r*millimeter}); skSolve(sk);
    opExtrude(context,id+"ex",{"entities":qSketchRegion(id+"sk",false),"direction":axis,
        "endBound":BoundingType.BLIND,"endDepth":h*millimeter});
    opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});
    return lwOne(context,qCreatedBy(id+"ex",EntityType.BODY));
}
function lwCut(context is Context,id is Id,a is Query,b is Query) returns Query
{
    opBoolean(context,id,{"targets":a,"tools":b,"operationType":BooleanOperationType.SUBTRACTION});
    return lwOne(context,qUnion([a,qCreatedBy(id,EntityType.BODY)]));
}
function lwJoin(context is Context,id is Id,a is Query,b is Query) returns Query
{
    opBoolean(context,id,{"tools":qUnion([a,b]),"operationType":BooleanOperationType.UNION});
    return lwOne(context,qUnion([a,b,qCreatedBy(id,EntityType.BODY)]));
}
function lwName(context is Context,q is Query,n is string,c is Color)
{
    setProperty(context,{"entities":q,"propertyType":PropertyType.NAME,"value":n});
    setProperty(context,{"entities":q,"propertyType":PropertyType.APPEARANCE,"value":c});
}
function lwBeamYZ(context is Context,id is Id,x,y0,z0,y1,z1,width,thickness) returns Query
{
    var v=normalize(vector(y1-y0,z1-z0)); var n=vector(-v[1],v[0])*width/2;
    return lwPrism(context,id,plane(vector(x,0,0)*millimeter,vector(1,0,0),vector(0,1,0)),
        [[y0+n[0],z0+n[1]],[y1+n[0],z1+n[1]],[y1-n[0],z1-n[1]],[y0-n[0],z0-n[1]]],thickness);
}
function lwSphere(context is Context,id is Id,p is Vector,r) returns Query
{
    var sk=newSketchOnPlane(context,id+"sk",{"sketchPlane":plane(p*millimeter,vector(0,-1,0),vector(1,0,0))});
    skArc(sk,"arc",{"start":vector(0,-r)*millimeter,"mid":vector(r,0)*millimeter,"end":vector(0,r)*millimeter});
    skLineSegment(sk,"axis",{"start":vector(0,r)*millimeter,"end":vector(0,-r)*millimeter}); skSolve(sk);
    opRevolve(context,id+"rev",{"entities":qSketchRegion(id+"sk",false),"axis":line(p*millimeter,vector(0,0,1)),"angleForward":360*degree});
    opDeleteBodies(context,id+"clean",{"entities":qCreatedBy(id+"sk",EntityType.BODY)});
    return lwOne(context,qCreatedBy(id+"rev",EntityType.BODY));
}
function lwCord(context is Context,id is Id,a is Vector,b is Vector) returns Query
{ return lwCylinder(context,id,a,normalize(b-a),1.25,norm(b-a)); }
const LW_WIDTH={(millimeter):[560,600,640]} as LengthBoundSpec;
const LW_PH={(millimeter):[330,350,370]} as LengthBoundSpec;
const LW_FRONT={(millimeter):[5,6,8]} as LengthBoundSpec;
const LW_BACK={(millimeter):[3,4,6]} as LengthBoundSpec;
const LW_DEPTH={(millimeter):[44,48,60]} as LengthBoundSpec;
const LW_BALL={(millimeter):[26,30,32]} as LengthBoundSpec;
annotation {"Feature Type Name":"Halloween Lochwand R1"}
export const lochwand = defineFeature(function(context is Context,id is Id,definition is map)
    precondition
    {
        annotation {"Name":"Panel width"} isLength(definition.width,LW_WIDTH);
        annotation {"Name":"One of three panel heights"} isLength(definition.panelHeight,LW_PH);
        annotation {"Name":"Front plywood thickness - assumed"} isLength(definition.front,LW_FRONT);
        annotation {"Name":"Back plywood thickness - assumed"} isLength(definition.back,LW_BACK);
        annotation {"Name":"True clear cavity depth"} isLength(definition.depth,LW_DEPTH);
        annotation {"Name":"Ball diameter - assumed"} isLength(definition.ball,LW_BALL);
        annotation {"Name":"Open return review view","Default":false} definition.returnView is boolean;
    }
    {
        var W=definition.width/millimeter; var P=definition.panelHeight/millimeter;
        var F=definition.front/millimeter; var B=definition.back/millimeter;
        var D=definition.depth/millimeter; var R=definition.ball/millimeter/2;
        var Z0=250; var H=P*3; var top=Z0+H; var I=W-48;
        var plywood=color(0.82,0.70,0.49); var backColor=color(0.65,0.57,0.43);
        var wood=color(0.57,0.37,0.18); var pla=color(0.84,0.29,0.10);
        var green=color(0.04,0.43,0.34); var metal=color(0.45,0.47,0.47);
        // x,z,r. Coordinates refer to the 600 x 1050 reference panel set.
        var holes=[[-210,455,22],[-125,455,22],[45,455,22],[130,455,22],[215,455,22],[-210,535,22],[-40,535,22],[45,535,22],[130,535,22],[215,535,22],[-210,665,22],[-125,665,22],[-40,665,22],[130,665,22],[215,665,22],[-210,745,22],[-125,745,22],[-40,745,22],[45,745,22],[215,745,22],[-210,825,22],[-125,825,22],[45,825,22],[130,825,22],[215,825,22],[-210,905,22],[-40,905,22],[45,905,22],[130,905,22],[215,905,22],[-210,1000,22],[-125,1000,22],[-40,1000,22],[130,1000,22],[215,1000,22],[-210,1080,22],[-125,1080,22],[-40,1080,22],[45,1080,22],[215,1080,22],[-210,1160,22],[-125,1160,22],[45,1160,22],[130,1160,22],[215,1160,22],[-210,1240,22],[-125,1240,22],[-40,1240,22],[45,1240,22],[180,1240,24]];
        for(var k=0;k<3;k+=1)
        {
            var zl=Z0+k*P; var zu=zl+P;
            var back=lwBox(context,id+("back"~k),-W/2,D,zl,W/2,D+B,zu);
            lwName(context,back,"B"~(k+1)~" BACK plywood "~W~" x "~P~" x "~B,backColor);
            if(!definition.returnView)
            {
                var panel=lwBox(context,id+("front"~k),-W/2,-F,zl,W/2,0,zu);
                if(k==0)panel=lwCut(context,id+"exitCut",panel,lwBox(context,id+"exitTool",-I/2,-F-1,Z0-1,I/2,1,Z0+110));
                for(var j=0;j<size(holes);j+=1)
                {
                    var hz=Z0+(holes[j][1]-250)*H/1050; var hx=holes[j][0]*W/600;
                    if(hz>zl && hz<zu)
                        panel=lwCut(context,id+("holeCut"~j),panel,lwCylinder(context,id+("hole"~j),vector(hx,-F-1,hz),vector(0,1,0),holes[j][2],F+2));
                }
                for(var side in [-1,1]) for(var row=0;row<3;row+=1)
                {
                    var sx=side*(W/2-12); var sz=zl+25+row*(P-50)/2;
                    panel=lwCut(context,id+("fixCut"~k~"s"~side~"r"~row),panel,lwCylinder(context,id+("fix"~k~"s"~side~"r"~row),vector(sx,-F-1,sz),vector(0,1,0),2,F+2));
                }
                lwName(context,panel,"F"~(k+1)~" FRONT laser plywood "~W~" x "~P~" x "~F,plywood);
            }
        }
        // Side battens establish true inner faces y0 and yD. No screw end enters chamber.
        for(var side in [-1,1])
        {
            var xl=side<0 ? -W/2 : W/2-24;
            lwName(context,lwBox(context,id+("stile"~side),xl,0,0,xl+24,D,top+24),"TIMBER side stile "~side,wood);
        }
        lwName(context,lwBox(context,id+"header",-I/2,0,top,I/2,D,top+24),"TIMBER top rail 24 x "~D,wood);
        // Every horizontal seam rail is wholly BEHIND the back sheet.
        for(var k=0;k<4;k+=1)
        {
            var zc=Z0+k*P;
            lwName(context,lwBox(context,id+("rearTie"~k),-W/2,D+B,zc-12,W/2,D+B+48,zc+12),"TIMBER external rear tie "~(k+1),wood);
        }
        // Ramp/floor are flat sheet solids with complementary end bevels represented.
        // Blank projection along slope is < 105 mm; end dressing remains a shop operation.
        var run=D+10; var slope=75/run; var verticalT=B*sqrt(1+slope*slope);
        var ramp=lwPrism(context,id+"ramp",plane(vector(-I/2,0,0)*millimeter,vector(1,0,0),vector(0,1,0)),
            [[-10,Z0+20],[D,Z0+95],[D,Z0+95-verticalT],[-10,Z0+20-verticalT]],I);
        lwName(context,ramp,"R1 RETURN RAMP plywood - blank "~I~" x 105; dress ends",plywood);
        var tf=Z0+20-120*tan(13*degree); var trayT=B/cos(13*degree);
        lwName(context,lwPrism(context,id+"tray",plane(vector(-I/2,0,0)*millimeter,vector(1,0,0),vector(0,1,0)),
            [[-130,tf],[-10,Z0+20],[-10,Z0+20-trayT],[-130,tf-trayT]],I),"T1 OUTPUT FLOOR plywood - blank "~I~" x 126",plywood);
        lwName(context,lwBox(context,id+"trayLip",-I/2,-134,tf-B,I/2,-130,tf+35),"T2 OUTPUT LIP plywood "~I~" x "~(35+B),plywood);
        for(var side in [-1,1])
        {
            var xl=side<0 ? -I/2-B : I/2;
            lwName(context,lwPrism(context,id+("traySide"~side),plane(vector(xl,0,0)*millimeter,vector(1,0,0),vector(0,1,0)),
                [[-134,tf-B],[-10,Z0+20-trayT],[-10,Z0+50],[-134,tf+35]],B),"T3/T4 OUTPUT SIDE plywood "~side,plywood);
        }
        if(!definition.returnView)
        {
            // Stepped retaining pocket: front aperture 24 < ball; rear 36 > ball.
            var cy=-F-R; var cz=Z0+150; var hc=cz+3;
            var hFront=-F-32; var hStep=-F-27.5; var hBack=-F-2;
            var holder=lwCylinder(context,id+"holderBlank",vector(0,hFront,hc),vector(0,1,0),38,30);
            holder=lwCut(context,id+"frontAperture",holder,lwCylinder(context,id+"frontApertureTool",vector(0,hFront-1,hc),vector(0,1,0),12,32));
            holder=lwCut(context,id+"rearPocket",holder,lwCylinder(context,id+"rearPocketTool",vector(0,hStep,hc),vector(0,1,0),R+3,27));
            // Open top loading channel, connected only to rear pocket; front rim remains.
            holder=lwCut(context,id+"loadingNotch",holder,lwBox(context,id+"loadingTool",-R-1,hStep,hc,R+1,hBack+1,hc+40));
            for(var side in [-1,1])
            {
                var ear=lwCylinder(context,id+("ear"~side),vector(side*39,hFront+8,hc+17),vector(0,1,0),9,12);
                holder=lwJoin(context,id+("earJoin"~side),holder,ear);
                holder=lwCut(context,id+("earBore"~side),holder,lwCylinder(context,id+("earTool"~side),vector(side*39,hFront+7,hc+17),vector(0,1,0),2,14));
            }
            for(var signX in [-1,1]) for(var signZ in [-1,1])
            {
                var foot=lwCylinder(context,id+("pad"~signX~"z"~signZ),vector(signX*25,hBack-0.2,hc+signZ*21),vector(0,1,0),4,1.4);
                holder=lwJoin(context,id+("padJoin"~signX~"z"~signZ),holder,foot);
            }
            lwName(context,holder,"PLA CARRIER R1 - rear 36 / front 24; loading slot; 4 skids",pla);
            lwName(context,lwSphere(context,id+"ball",vector(0,cy,cz),R),"REFERENCE BALL diameter "~(2*R),color(0.98,0.72,0.11));
            for(var side in [-1,1])
            {
                var gx=side*(W/2-24); var gz=top+32; var gy=-F-18;
                var guide=lwBox(context,id+("guideBase"~side),gx-12,-F-25,top+4,gx+12,0,top+24);
                guide=lwJoin(context,id+("guideJoin"~side),guide,lwCylinder(context,id+("guideEye"~side),vector(gx,gy-5,gz),vector(0,1,0),12,10));
                guide=lwCut(context,id+("guideBore"~side),guide,lwCylinder(context,id+("guideTool"~side),vector(gx,gy-6,gz),vector(0,1,0),5,12));
                lwName(context,guide,"PLA TOP CORD GUIDE "~side~" - polish eye; fastening TBD",pla);
                lwName(context,lwCord(context,id+("cordLift"~side),vector(side*39,hFront+14,hc+17),vector(gx,gy,gz)),"REFERENCE CORD lift "~side,green);
                lwName(context,lwCord(context,id+("cordTail"~side),vector(gx,gy,gz),vector(gx,-F-18,Z0+60)),"REFERENCE CORD hand end "~side,green);
                var grip=lwCylinder(context,id+("grip"~side),vector(gx,-F-18,Z0+20),vector(0,0,1),10,40);
                grip=lwCut(context,id+("gripHole"~side),grip,lwCylinder(context,id+("gripTool"~side),vector(gx,-F-18,Z0+19),vector(0,0,1),2,42));
                lwName(context,grip,"PLA HAND GRIP "~side,pla);
            }
        }
        var cs=cos(8*degree); var sn=sin(8*degree);
        var tilt=matrix([[1,0,0],[0,cs,sn],[0,-sn,cs]]);
        opTransform(context,id+"boardLean",{"bodies":qBodyType(qEverything(EntityType.BODY),BodyType.SOLID),"transform":transform(tilt,vector(0,0,0)*millimeter)});
        // Bevel upright bottoms to meet horizontal foot tops at global Z24.
        var floorTool=lwBox(context,id+"bottomTool",-W,-500,-500,W,1000,24);
        opBoolean(context,id+"bottomLevel",{"targets":qSubtraction(qBodyType(qEverything(EntityType.BODY),BodyType.SOLID),floorTool),
            "tools":floorTool,"operationType":BooleanOperationType.SUBTRACTION});
        for(var side in [-1,1])
        {
            var xc=side*(W/2-12); var xleft=xc-12;
            lwName(context,lwBox(context,id+("groundFoot"~side),xc-24,-170,0,xc+24,620,24),"TIMBER ground foot 24 x 48 x 790 "~side,wood);
            var upper=tilt*vector(0,D+B+48,top);
            var leg=lwBeamYZ(context,id+("rearLeg"~side),xleft,590,24,upper[1],upper[2],48,24);
            leg=lwCut(context,id+("legFootTrim"~side),leg,lwBox(context,id+("legTrimTool"~side),-W,-500,-100,W,1000,24));
            var legFront=lwBox(context,id+("legFrontTool"~side),-W,-1000,0,W,D+B+48,top+200);
            opTransform(context,id+("legFrontTilt"~side),{"bodies":legFront,"transform":transform(tilt,vector(0,0,0)*millimeter)});
            leg=lwCut(context,id+("legFrontTrim"~side),leg,legFront);
            lwName(context,leg,"TIMBER rear strut 24 x 48 "~side~" - butt to top tie",wood);
            var braceStart=tilt*vector(0,D+B+48,Z0+P);
            var lowZ=330; var lowY=590+(upper[1]-590)*(lowZ-24)/(upper[2]-24);
            var bx=side<0 ? -W/2+24 : W/2-48;
            var brace=lwBeamYZ(context,id+("brace"~side),bx,braceStart[1],braceStart[2],lowY,lowZ,48,24);
            var braceFront=lwBox(context,id+("braceFrontTool"~side),-W,-1000,0,W,D+B+48,top+200);
            opTransform(context,id+("braceFrontTilt"~side),{"bodies":braceFront,"transform":transform(tilt,vector(0,0,0)*millimeter)});
            brace=lwCut(context,id+("braceFrontTrim"~side),brace,braceFront);
            lwName(context,brace,"TIMBER removable brace "~side~" - butt to middle tie; side to strut",wood);
        }
        // Solid count and true bounds are verified through the native parts/bounds endpoints.
    });
