#******************************************************************************
# * Copyright (c) 2019, XtremeDV. All rights reserved.
# *
# * Licensed under the Apache License, Version 2.0 (the "License");
# * you may not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# *
# * http://www.apache.org/licenses/LICENSE-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.
# *
# * Author: Jude Zhang, Email: zhajio.1988@gmail.com
# *******************************************************************************
# Copyright (c) 2019-2020, Jude Zhang zhajio.1988@gmail.com

import logging
import os

from buildCfg import *
from groupCfg import *

logger = logging.getLogger(__name__)

class readCfgFileBase(baseCfg):
    def __init__(self, name, file):
        if not os.path.isfile(file):
            logger.error("Configuration file not found: '%s'", file)
            raise IOError("Configuration file not found: '%s'" % file)
        try:
            self._section = ConfigObj(infile=file, stringify=True)
        except IOError as e:
            logger.error("Failed to read configuration file '%s': %s", file, e)
            raise
        except ParseError as e:
            logger.error("Failed to parse configuration file '%s': %s", file, e)
            raise
        logger.info("Successfully loaded configuration file: '%s'", file)
        super(readCfgFileBase, self).__init__(name, self._section, None)
        self._subSectionType = {}
        self._validSection = ['build', 'testgroup']

    def _readSubSection(self):
        for k, v in getSections(self._section).items():
            if self._checkSubSection(k) and k in self._subSectionType:
                try:
                    self._subSection[k] = self._subSectionType[k](k, v, self)
                    self._subSection[k].parse()
                except ParseError as e:
                    logger.error("Error parsing section [%s]: %s", k, e)
                    raise
            elif k not in self._subSectionType:
                logger.warning("Section [%s] is valid but has no registered handler; skipping", k)

    def _checkSubSection(self, key):
        if key not in self._validSection:
            logger.error("Unknown configuration section: [%s]. Valid sections are: %s",
                         key, self._validSection)
            raise ParseError("[%s] is unknown section. Valid sections are: %s" % (key, self._validSection))
        return True
    
    
class readBuildCfgFile(readCfgFileBase):
    def __init__(self, file):
        super(readBuildCfgFile, self).__init__('readBuildCfgFile', file)
        self._subSectionType = {'build': buildCfg}
        self.parse()

    @property
    def build(self):
        if 'build' in self.subSection:
            return self.subSection['build']
        logger.warning("No [build] section found in build configuration file")
        return None

    def getBuild(self, build=''):
        if self.build is None:
            logger.error("Cannot retrieve build '%s': no [build] section in configuration", build)
            raise ParseError("No [build] section found in build configuration")
        return self.build.getBuild(build)


    def compileOption(self, buildName):
        if self.build is None:
            logger.error("Cannot get compile options: no [build] section in configuration")
            raise ParseError("No [build] section found in build configuration")
        return self._toList(self.build.compileOption) + self._toList(self.getBuild(buildName).compileOption) if self.build.compileOption else self.getBuild(buildName).compileOption

    def simOption(self, buildName):
        if self.build is None:
            logger.error("Cannot get sim options: no [build] section in configuration")
            raise ParseError("No [build] section found in build configuration")
        return self._toList(self.build.simOption) + self._toList(self.getBuild(buildName).simOption) if self.build.simOption else self.getBuild(buildName).simOption

    def preCompileOption(self, buildName):
        if self.build is None:
            logger.error("Cannot get pre-compile options: no [build] section in configuration")
            raise ParseError("No [build] section found in build configuration")
        return self._toList(self.build.preCompileOption) + self._toList(self.getBuild(buildName).preCompileOption)

    def preSimOption(self, buildName):
        if self.build is None:
            logger.error("Cannot get pre-sim options: no [build] section in configuration")
            raise ParseError("No [build] section found in build configuration")
        return self._toList(self.build.preSimOption) + self._toList(self.getBuild(buildName).preSimOption)

    def postCompileOption(self, buildName):
        if self.build is None:
            logger.error("Cannot get post-compile options: no [build] section in configuration")
            raise ParseError("No [build] section found in build configuration")
        return self._toList(self.build.postCompileOption) + self._toList(self.getBuild(buildName).postCompileOption)

    def postSimOption(self, buildName):
        if self.build is None:
            logger.error("Cannot get post-sim options: no [build] section in configuration")
            raise ParseError("No [build] section found in build configuration")
        return self._toList(self.build.postSimOption) + self._toList(self.getBuild(buildName).postSimOption)

    def _toList(self, preOptions):
        if isinstance(preOptions, str):
            return [preOptions]
        elif isinstance(preOptions, list):
            return preOptions
        elif preOptions is None:
            return []
        else:
            logger.warning("Unexpected option type '%s' for value: %s; returning as single-element list",
                           type(preOptions).__name__, preOptions)
            return [preOptions]

class readGroupCfgFile(readCfgFileBase):
    def __init__(self, file):
        super(readGroupCfgFile, self).__init__('readGroupCfgFile', file)
        self._subSectionType = {'testgroup': groupCfg}
        self.parse()
        self._validBuild = []
        self._allBuild = []
        self._tests = {}

    @property
    def testGroup(self):
        if 'testgroup' in self.subSection:
            return self.subSection['testgroup']
        logger.warning("No [testgroup] section found in group configuration file")
        return None

    @property
    def validBuild(self):
        if not self._validBuild:
            logger.error("No valid builds found; ensure group configuration specifies a build")
            raise ValueError("No valid builds found in group configuration")
        return self._validBuild[0]

    @property
    def allBuild(self):
        return list(set(self._allBuild))

    def getTests(self, groupName):
        if self.testGroup is None:
            logger.error("Cannot retrieve tests for group '%s': no [testgroup] section in configuration", groupName)
            raise ParseError("No [testgroup] section found in group configuration")
        groupSection = self.testGroup.getGroup(groupName)
        globalBuild = groupSection.buildOption
        globalTests = groupSection.testsOption
        if globalBuild:
            self._validBuild.append(globalBuild)
            self._allBuild.append(globalBuild)
        if globalTests:
            self._tests[groupName] = globalTests
        if groupSection.include:
            for incGroup in groupSection.incGroups:
                if incGroup.testsOption:
                    self._tests[incGroup.name] = incGroup.testsOption
                self.setValidBuild(globalBuild, incGroup.buildOption)
                self._allBuild.append(incGroup.buildOption)

        self.checkBuild(self._validBuild, groupName)
        return self._tests

    def setValidBuild(self, globalBuild, subBuild):
        if globalBuild and subBuild and globalBuild != subBuild:
            self._validBuild.append(globalBuild)
        elif subBuild and not globalBuild:
            self._validBuild.append(subBuild)
        elif globalBuild and not subBuild:
            self._validBuild.append(globalBuild)

    def checkBuild(self, buildList, groupName):
        buildSet = set(buildList)
        if len(buildSet) != 1:
            logger.error("Group '%s' has inconsistent builds across subgroups: %s. "
                         "All included subgroups must use the same build.",
                         groupName, list(buildSet))
            raise ValueError("Group '%s' has included subgroups that must all use the same build, "
                             "but found: %s" % (groupName, list(buildSet)))

if __name__ == '__main__':
#    config = readBuildCfgFile(defaultBuildFile())
#    print(config.build.simOption)
#    print(config.build.compileOption)
#    print(config.build.getBuild('dla').name)
#    print(config.build.getBuild('dla').compileOption)
#    print(config.simOption('dla'))
#    print(config.preCompileOption('dla'))
#    print(config.postCompileOption('dla'))
#    print(config.preSimOption('dla'))
#    print(config.postSimOption('dla'))


    config = readGroupCfgFile(defaultGroupFile())
    config.getTests('v1_regr')
    config.getTests('top_regr')

    #for v in config.testgroup.subSection.values():
    #    print(v.include)
    #    print(v.name)
        #print(v.buildOption)
        #print(v.argsOption)
        #print(v.testsOption)
        #print('haha', v.include)
        #for include in v.include:
        #   print(config.getGroup(include).testsOption)
