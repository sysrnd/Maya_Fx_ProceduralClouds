import maya.cmds as cmds
import maya.mel as mel

class ProceduralClouds(object):

	def __init__(self):
		#load nearestPointOnMesh in case it isn't
		self.loadPlugin()

		self.cloudsGeo = self.getAllCloudsGeo()
		self.emitters = []

	def mainClouds(self):

		print self.cloudsGeo

		for cloud in self.cloudsGeo:

			cloudShape = cmds.listRelatives(cloud, s=True, f=True)[0]
			#get its BoundingBox
			BB = self.getBB(cloud)
			#create3DFluid
			fluidShape = self.create3DFluid(BB, cloud)
			#initialConfig
			self.initialFluidsConfig(fluidShape)
			#move Fluid to Geo
			self.toPos(cloud, fluidShape)
			#connect Closest Node to cloud
			closNode = self.closestNode(cloudShape)
			#fill
			self.fillWVoxels(cloud, fluidShape, closNode)
			#deleteClosNode
			self.deleteClosestNode(closNode)

			cmds.setAttr(cloudShape + '.visibility', 0)

	def mainRain(self):

		for cloud in self.cloudsGeo:

			#duplicateMesh
			dupCloud = cmds.duplicate(cloud, n=cloud + '_dupnParticles')[0]
			#get rainyfaces
			faces = self.getRainyFaces(dupCloud)
			#delete others
			self.deleteFaces(dupCloud, faces)
			#createParticlezz
			self.createParticles(dupCloud)

	def loadPlugin(self):
		if cmds.pluginInfo('nearestPointOnMesh.mll', q=True, l=True) == False:
			cmds.loadPlugin('nearestPointOnMesh.mll')

	def initialFluidsConfig(self, fluidShape):
		'''
		'''
		cmds.setAttr(fluidShape + ".squareVoxels", 1)
		cmds.setAttr(fluidShape + ".densityMethod", 2)
		cmds.setAttr(fluidShape + ".selfShadowing", 1);
		cmds.setAttr(fluidShape + ".velocityDamp", 0.3);

	def closestNode(self, geo):
		'''
		'''
		
		closestNode = cmds.shadingNode('nearestPointOnMesh', asUtility=True, n=geo + '_closest')
		cmds.connectAttr(geo + '.worldMesh', closestNode + '.inMesh')

		return closestNode

	def deleteClosestNode(self, node):

		cmds.delete(node)

	def getAllCloudsGeo(self):
		'''
		'''
		_cloudsGeo = []

		for mesh in cmds.ls(et='mesh'):
			isValidCloud = False
			if mesh.lower().find('nube') != -1:
				isValidCloud = True

			if mesh.lower().find('_dupnParticles') != -1:
				isValidCloud = False

			meshParent = cmds.listRelatives(mesh, p=True)[0]
			children = cmds.listRelatives(meshParent, c=True)

			if type(children) == list:
				for child in children:
					if child.find('fluid') != -1:
						isValidCloud = False

			if isValidCloud == True:

				cmds.setAttr(mesh + '.visibility', 1)
				_cloudsGeo.append(meshParent)

		return _cloudsGeo

	def parentTo(src, dest):

		parent = cmds.parent(src, dest)
		return parent

	def getBB(self, geo):
		'''
		'''
		BBSum = []

		BB = cmds.xform(geo, q=True, boundingBox = True)

		for x in xrange(0, (len(BB) - 3)):
			
			axisSum = BB[x + 3] - BB[x]
			axisSum = axisSum * 1
			axisSum = round(axisSum, 0)
			BBSum.append(axisSum)

		return BBSum

	def toPos(self, geo, fluidShape):
		'''
		'''

		fluidParent = cmds.listRelatives(fluidShape, p=True, f=True)

		cons = cmds.pointConstraint(geo, fluidParent, mo=False)
		cmds.delete(cons)			

	def create3DFluid(self, BB, geo):
		
		multiplier = 1

		BBRes = [i * multiplier for i in BB]

		fluidShape = mel.eval('create3DFluid %s %s %s %s %s %s;' % (BBRes[0], BBRes[1], BBRes[2], BB[0], BB[1], BB[2]))

		fluid = cmds.listRelatives(fluidShape, p=True)[0]
		cmds.parent(fluid, geo)


		return fluidShape

	def fillWVoxels(self, geo, fluidShape, closNode):

		resX, resY, resZ = cmds.getAttr(fluidShape + '.resolution')[0]

		for x in range(resX):
			for y in range(resY):
				for z in range(resZ):

					voxelCenter = cmds.fluidVoxelInfo(fluidShape, voxelCenter = True, xi=x, yi=y, zi=z)
					cmds.setAttr(closNode + '.inPositionX', voxelCenter[0])
					cmds.setAttr(closNode + '.inPositionY', voxelCenter[1])
					cmds.setAttr(closNode + '.inPositionZ', voxelCenter[2])

					closestPtX = cmds.getAttr(closNode + '.positionX')
					closestPtY = cmds.getAttr(closNode + '.positionY')
					closestPtZ = cmds.getAttr(closNode + '.positionZ')
					closPos = [closestPtX, closestPtY, closestPtZ]

					ClosPos = [a - b for a, b in zip(voxelCenter, closPos)]

					normalX = cmds.getAttr(closNode + '.normalX')
					normalY = cmds.getAttr(closNode + '.normalY')
					normalZ = cmds.getAttr(closNode + '.normalZ')

					normals = [normalX, normalY, normalZ]

					dotProduct = sum(i*j for i,j in zip(normals, ClosPos))
					if dotProduct <= 0:
						#replace 0.5 with dotPr clamped
						density = "setFluidAttr -at \"density\" -ad -fv " + str(0.3) + " -xi " + str(x) + " -yi " + str(y) + " -zi " + str(z) + " " + fluidShape + ";";
						mel.eval(density)

			cmds.select(fluidShape)
			mel.eval('doSetFluidState 1 { "1", 1, 1, 1, 1, 1, 1 };')

	def getRainyFaces(self, geo):
	    
	    tolerance = 60
	    axis = (0, -1, 0)
	    
	    cmds.select(geo + ".f[*]")
	    cmds.polySelectConstraint(mode = 3, type = 8, orient = 2, orientaxis = axis, orientbound = (0, tolerance))
	    cmds.polySelectConstraint(dis=True)
	    
	    sel = cmds.ls(sl=True, fl=True)
	    
	    BB = cmds.xform(geo, q=True, ws=True, bb=True)
	    threshold = .25
	    BBYaxis = (BB[4] - BB[1]) * threshold
	    BBThreshold = BBYaxis + BB[1]
	    
	    faces = cmds.polyEvaluate(geo, f=True)
	    listFaces = []
	    listFacesInv = []    
	    
	    for face in sel:
	      
	        if cmds.xform(face, q=True, ws=True, t=True)[1] < BBThreshold:
	                listFaces.append(face)
	                
	    for f in xrange(0, faces):
	        
	        stringFace = geo + '.f[' + str(f) + ']'
	        if stringFace not in listFaces:
	            listFacesInv.append(stringFace)
	            
	        
	    return listFacesInv
       
	def deleteFaces(self, geo, listFaces):

		cmds.delete(listFaces)
		cmds.delete(geo, ch=True)
		cmds.select(cl=True)

		cmds.setAttr(geo + '.visibility', 0)

	def createParticles(self, geo):

		emitterVar = cmds.emitter(geo, type='surface', r=1)[0]
		nParticleVar = cmds.nParticle()[0]
		cmds.connectDynamic(nParticleVar, em=emitterVar)

		nParticleShape = cmds.listRelatives(nParticleVar, s=True)[0]

		self.tryAddingDefaultArgs(nParticleShape)

		cmds.setAttr(nParticleShape + '.enableSPH', 1)
		cmds.setAttr(nParticleShape + '.incompressibility', 1)
		cmds.setAttr(nParticleShape + '.restDensity', 2)
		cmds.setAttr(nParticleShape + '.radiusScaleSPH', 0)
		cmds.setAttr(nParticleShape + '.viscosity', 0.1)
		cmds.setAttr(nParticleShape + '.threshold', 0.001)
		cmds.setAttr(nParticleShape + '.blobbyRadiusScale', 0.01)
		cmds.setAttr(nParticleShape + '.motionStreak', 8)
		cmds.setAttr(nParticleShape + '.meshTriangleSize', 0.001)
		cmds.setAttr(nParticleShape + '.maxTriangleResolution', 300)
		cmds.setAttr(nParticleShape + '.particleRenderType', 6)
		cmds.setAttr(nParticleShape + '.tailSize', 9.5)

		return emitterVar, nParticleVar

	def tryAddingDefaultArgs(self, nParticleShape):

		commands = ['addAttr -is true -ln "colorAccum" -at bool -dv false %s;'
					,'addAttr -is true -ln "useLighting" -at bool -dv false %s;'
					,'addAttr -is true -ln "lineWidth" -at long -min 1 -max 20 -dv 1 %s;'
					,'addAttr -is true -ln "tailFade" -at "float" -min -1 -max 1 -dv 0 %s;'
					,'addAttr -is true -ln "tailSize" -at "float" -min -100 -max 100 -dv 1 %s;'
					,'addAttr -is true -ln "normalDir" -at long -min 1 -max 3 -dv 2 %s;'
					]

		for command in commands:
			try:
				mel.eval(command % nParticleShape)
			except:
				pass

	def setHierarchy(self):
		pass
	
	def masterLoc(self):

		loc = cmds.spaceLocator()


clouds = ProceduralClouds()
clouds.mainRain()
clouds.mainClouds()