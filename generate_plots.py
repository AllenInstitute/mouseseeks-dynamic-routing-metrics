import os
import re
import h5py
import numpy as np
import scipy.stats
import matplotlib
import matplotlib.pyplot as plt


matplotlib.rcParams['pdf.fonttype'] = 42


def adjustResponseRate(r, n):
    if r == 0:
        r = 0.5/n
    elif r == 1:
        r = 1 - 0.5/n
    return r


def calcDprime(hitRate, falseAlarmRate, goTrials, nogoTrials):
    hr = adjustResponseRate(hitRate, goTrials)
    far = adjustResponseRate(falseAlarmRate, nogoTrials)
    z = [scipy.stats.norm.ppf(r) for r in (hr, far)]
    return z[0]-z[1]


class DynRoutData():
    
    def __init__(self):
        self.frameRate = 60
        self.engagedThresh = 10
    
    
    def loadBehavData(self,filePath):

        self.behavDataPath = filePath
        
        d = h5py.File(self.behavDataPath,'r')
        
        # self.subjectName = d['subjectName'][()]
        self.subjectName = re.search('.*_([0-9]{6})_',os.path.basename(self.behavDataPath)).group(1)
        self.rigName = d['rigName'].asstr()[()]
        self.computerName = d['computerName'].asstr()[()] if 'computerName' in d and  d['computerName'].dtype=='O' else None
        self.taskVersion = d['taskVersion'].asstr()[()] if 'taskVersion' in d else None
        self.startTime = d['startTime'].asstr()[()]
        
        self.frameIntervals = d['frameIntervals'][:]
        self.frameTimes = np.concatenate(([0],np.cumsum(self.frameIntervals)))
        
        self.trialEndFrame = d['trialEndFrame'][:]
        self.trialEndTimes = self.frameTimes[self.trialEndFrame]
        self.nTrials = self.trialEndFrame.size
        self.trialStartFrame = d['trialStartFrame'][:self.nTrials]
        self.trialStartTimes = self.frameTimes[self.trialStartFrame]
        self.stimStartFrame = d['trialStimStartFrame'][:self.nTrials]
        self.stimStartTimes = self.frameTimes[self.stimStartFrame]
        
        self.newBlockAutoRewards = d['newBlockAutoRewards'][()]
        self.newBlockGoTrials = d['newBlockGoTrials'][()]
        self.newBlockNogoTrials = d['newBlockNogoTrials'][()] if 'newBlockNogoTrials' in d else 0
        self.newBlockCatchTrials = d['newBlockCatchTrials'][()] if 'newBlockCatchTrials' in d else 0
        self.autoRewardOnsetFrame = d['autoRewardOnsetFrame'][()]
        
        self.trialRepeat = d['trialRepeat'][:self.nTrials]
        self.incorrectTrialRepeats = d['incorrectTrialRepeats'][()]
        self.incorrectTimeoutFrames = d['incorrectTimeoutFrames'][()]
        
        self.quiescentFrames = d['quiescentFrames'][()]
        self.quiescentViolationFrames = d['quiescentViolationFrames'][:] if 'quiescentViolationFrames' in d.keys() else d['quiescentMoveFrames'][:]    
        
        self.responseWindow = d['responseWindow'][:]
        self.responseWindowTime = np.array(self.responseWindow)/self.frameRate
        
        self.trialStim = d['trialStim'].asstr()[:self.nTrials]
        self.trialBlock = d['trialBlock'][:self.nTrials]
        self.blockTrial = np.concatenate([np.arange(np.sum(self.trialBlock==i)) for i in np.unique(self.trialBlock)])
        self.blockStartTimes = self.trialStartTimes[[np.where(self.trialBlock==i)[0][0] for i in np.unique(self.trialBlock)]]
        self.blockFirstStimTimes = self.stimStartTimes[[np.where(self.trialBlock==i)[0][0] for i in np.unique(self.trialBlock)]]
        self.blockStimRewarded = d['blockStimRewarded'].asstr()[:]
        self.rewardedStim = self.blockStimRewarded[self.trialBlock-1]
        
        self.rewardFrames = d['rewardFrames'][:]
        self.rewardTimes = self.frameTimes[self.rewardFrames]
        self.rewardSize = d['rewardSize'][:]
        self.trialResponse = d['trialResponse'][:self.nTrials]
        self.trialResponseFrame = d['trialResponseFrame'][:self.nTrials]
        self.trialRewarded = d['trialRewarded'][:self.nTrials]
        
        if 'trialAutoRewardScheduled' in d:
            self.autoRewardScheduled = d['trialAutoRewardScheduled'][:self.nTrials]
            self.autoRewarded = d['trialAutoRewarded'][:self.nTrials]
            if len(self.autoRewardScheduled) < self.nTrials:
                self.autoRewardScheduled = np.zeros(self.nTrials,dtype=bool)
                self.autoRewardScheduled[self.blockTrial < self.newBlockAutoRewards] = True
            if len(self.autoRewarded) < self.nTrials:
                self.autoRewarded = self.autoRewardScheduled & np.in1d(self.stimStartFrame+self.autoRewardOnsetFrame,self.rewardFrames)
        else:
            self.autoRewardScheduled = d['trialAutoRewarded'][:self.nTrials]
            self.autoRewarded = self.autoRewardScheduled & np.in1d(self.stimStartFrame+self.autoRewardOnsetFrame,self.rewardFrames)
        self.rewardEarned = self.trialRewarded & (~self.autoRewarded)
        
        
        self.responseTimes = np.full(self.nTrials,np.nan)
        self.responseTimes[self.trialResponse] = self.frameTimes[self.trialResponseFrame[self.trialResponse].astype(int)] - self.stimStartTimes[self.trialResponse]
        
        self.lickFrames = d['lickFrames'][:]
        if len(self.lickFrames) > 0:
            lickTimesDetected = self.frameTimes[self.lickFrames]
            self.minLickInterval = 0.05
            isLick = np.concatenate(([True], np.diff(lickTimesDetected) > self.minLickInterval))
            self.lickTimes = lickTimesDetected[isLick]
        else:
            self.lickTimes = np.array([])
        
        if 'rotaryEncoder' in d and isinstance(d['rotaryEncoder'][()],bytes) and d['rotaryEncoder'].asstr()[()] == 'digital':
            self.runningSpeed = np.concatenate(([np.nan],np.diff(d['rotaryEncoderCount'][:]) / d['rotaryEncoderCountsPerRev'][()] * 2 * np.pi * d['wheelRadius'][()] * self.frameRate))
        else:
            self.runningSpeed = None
        
        self.visContrast = d['visStimContrast'][()]
        self.trialVisContrast = d['trialVisStimContrast'][:self.nTrials]
        if 'gratingOri' in d:
            self.gratingOri = {key: d['gratingOri'][key][()] for key in d['gratingOri']}
        else:
            self.gratingOri = {key: d['gratingOri_'+key][()] for key in ('vis1','vis2')}
        self.trialGratingOri = d['trialGratingOri'][:self.nTrials]
        
        self.soundVolume = d['soundVolume'][()]
        self.trialSoundVolume = d['trialSoundVolume'][:self.nTrials]
        
        if 'optoVoltage' in d:
            self.optoVoltage = d['optoVoltage'][()]
            self.galvoVoltage = d['galvoVoltage'][()]
            self.trialOptoOnsetFrame = d['trialOptoOnsetFrame'][:self.nTrials]
            self.trialOptoDur = d['trialOptoDur'][:self.nTrials]
            self.trialOptoVoltage = d['trialOptoVoltage'][:self.nTrials]
            self.trialGalvoVoltage = d['trialGalvoVoltage'][:self.nTrials]
        if 'optoRegions' in d and len(d['optoRegions']) > 0:
            self.optoRegions = d['optoRegions'].asstr()[()]
            
        d.close()
        
        self.catchTrials = self.trialStim == 'catch'
        self.multimodalTrials = np.array(['+' in stim for stim in self.trialStim])
        self.goTrials = (self.trialStim == self.rewardedStim) & (~self.autoRewardScheduled)
        self.nogoTrials = (self.trialStim != self.rewardedStim) & (~self.catchTrials) & (~self.multimodalTrials)
        self.sameModalNogoTrials = self.nogoTrials & np.array([stim[:-1]==rew[:-1] for stim,rew in zip(self.trialStim,self.rewardedStim)])
        if 'distract' in self.taskVersion:
            self.otherModalGoTrials = self.nogoTrials & np.in1d(self.trialStim,('vis1','sound1'))
        else:
            self.otherModalGoTrials = self.nogoTrials & np.in1d(self.trialStim,self.blockStimRewarded)
        self.otherModalNogoTrials = self.nogoTrials & ~self.sameModalNogoTrials & ~self.otherModalGoTrials
        
        self.hitTrials = self.goTrials & self.trialResponse
        self.missTrials = self.goTrials & (~self.trialResponse)
        self.falseAlarmTrials =self. nogoTrials & self.trialResponse
        self.correctRejectTrials = self.nogoTrials & (~self.trialResponse)
        self.catchResponseTrials = self.catchTrials & self.trialResponse
        
        self.engagedTrials = np.ones(self.nTrials,dtype=bool)
        for i in range(self.nTrials):
            r = self.trialResponse[:i+1][self.goTrials[:i+1]]
            if r.size > self.engagedThresh:
                if r[-self.engagedThresh:].sum() < 1:
                    self.engagedTrials[i] = False
        
        self.catchResponseRate = []
        self.hitRate = []
        self.hitCount = []
        self.falseAlarmRate = []
        self.falseAlarmSameModal = []
        self.falseAlarmOtherModalGo = []
        self.falseAlarmOtherModalNogo = []
        self.dprimeSameModal = []
        self.dprimeOtherModalGo = []
        self.dprimeNonrewardedModal = []
        for blockInd,rew in enumerate(self.blockStimRewarded):
            blockTrials = (self.trialBlock == blockInd + 1) & self.engagedTrials & (~self.trialRepeat)
            self.catchResponseRate.append(self.catchResponseTrials[blockTrials].sum() / self.catchTrials[blockTrials].sum())
            self.hitRate.append(self.hitTrials[blockTrials].sum() / self.goTrials[blockTrials].sum())
            self.hitCount.append(self.hitTrials[blockTrials].sum())
            self.falseAlarmRate.append(self.falseAlarmTrials[blockTrials].sum() / self.nogoTrials[blockTrials].sum())
            sameModal = blockTrials & self.sameModalNogoTrials
            otherModalGo = blockTrials & self.otherModalGoTrials
            otherModalNogo = blockTrials & self.otherModalNogoTrials
            self.falseAlarmSameModal.append(self.falseAlarmTrials[sameModal].sum() / sameModal.sum())
            self.falseAlarmOtherModalGo.append(self.falseAlarmTrials[otherModalGo].sum() / otherModalGo.sum())
            self.falseAlarmOtherModalNogo.append(self.falseAlarmTrials[otherModalNogo].sum() / otherModalNogo.sum())
            self.dprimeSameModal.append(calcDprime(self.hitRate[-1],self.falseAlarmSameModal[-1],self.goTrials[blockTrials].sum(),sameModal.sum()))
            self.dprimeOtherModalGo.append(calcDprime(self.hitRate[-1],self.falseAlarmOtherModalGo[-1],self.goTrials[blockTrials].sum(),otherModalGo.sum()))
            self.dprimeNonrewardedModal.append(calcDprime(self.falseAlarmOtherModalGo[-1],self.falseAlarmOtherModalNogo[-1],otherModalGo.sum(),otherModalNogo.sum()))


def generate_lick_raster_all_trials(behavior_filepath: str):
    obj = DynRoutData()
    obj.loadBehavData(behavior_filepath)

    preTime = 4
    postTime = 4
    lickRaster = []
    fig = plt.figure(figsize=(8, 8))
    gs = matplotlib.gridspec.GridSpec(4, 1)
    ax = fig.add_subplot(gs[:3, 0])
    ax.add_patch(matplotlib.patches.Rectangle([-obj.quiescentFrames/obj.frameRate, 0], width=obj.quiescentFrames /
                 obj.frameRate, height=obj.nTrials+1, facecolor='r', edgecolor=None, alpha=0.2, zorder=0))
    ax.add_patch(matplotlib.patches.Rectangle([obj.responseWindowTime[0], 0], width=np.diff(
        obj.responseWindowTime), height=obj.nTrials+1, facecolor='g', edgecolor=None, alpha=0.2, zorder=0))
    for i, st in enumerate(obj.stimStartTimes):
        if not obj.engagedTrials[i]:
            ax.add_patch(matplotlib.patches.Rectangle(
                [-preTime, i+0.5], width=preTime+postTime, height=1, facecolor='0.5', edgecolor=None, alpha=0.2, zorder=0))
        lt = obj.lickTimes - st
        trialLickTimes = lt[(lt >= -preTime) & (lt <= postTime)]
        lickRaster.append(trialLickTimes)
        ax.vlines(trialLickTimes, i+0.5, i+1.5, colors='k')
        if obj.trialRewarded[i]:
            rt = obj.rewardTimes - st
            trialRewardTime = rt[(rt > 0) & (rt <= postTime)]
            mfc = 'b' if obj.autoRewarded[i] else 'none'
            ax.plot(trialRewardTime, i+1, 'o', mec='b', mfc=mfc, ms=4)
    for side in ('right', 'top'):
        ax.spines[side].set_visible(False)
    ax.tick_params(direction='out', top=False, right=False)
    ax.set_xlim([-preTime, postTime])
    ax.set_ylim([0.5, obj.nTrials+0.5])
    ax.set_yticks([1, obj.nTrials])
    ax.set_ylabel('trial')
    title = (obj.subjectName + ', ' + obj.rigName + ', ' + obj.taskVersion +
             '\n' + 'all trials (n=' + str(obj.nTrials) + '), engaged (n=' + str(obj.engagedTrials.sum()) + ', not gray)' +
             '\n' + 'filled blue circles: auto-reward, open circles: earned reward')
    ax.set_title(title)
    return fig


def generate_lick_latency(behavior_filepath: str):
    obj = DynRoutData()
    obj.loadBehavData(behavior_filepath)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    stimLabels = np.unique(obj.trialStim)
    notCatch = stimLabels != 'catch'
    clrs = np.zeros((len(stimLabels), 3)) + 0.5
    clrs[notCatch] = plt.cm.plasma(np.linspace(0, 0.85, notCatch.sum()))[:, :3]
    for stim, clr in zip(stimLabels, clrs):
        trials = (obj.trialStim == stim) & obj.trialResponse
        rt = obj.responseTimes[trials]
        rtSort = np.sort(rt)
        cumProb = [np.sum(rt <= i)/rt.size for i in rtSort]
        ax.plot(rtSort, cumProb, color=clr, label=stim)
    for side in ('right', 'top'):
        ax.spines[side].set_visible(False)
    ax.tick_params(direction='out', top=False, right=False)
    ax.set_xlim([0, obj.responseWindowTime[1]+0.1])
    ax.set_ylim([0, 1.02])
    ax.set_xlabel('response time (s)')
    ax.set_ylabel('cumulative probability')
    ax.legend()
    plt.tight_layout()
    return fig


def generate_run_speed_mean_block(behavior_filepath: str):
    obj = DynRoutData()
    obj.loadBehavData(behavior_filepath)

    preTime = 4
    postTime = 4

    runPlotTime = np.arange(-preTime, postTime+1 /
                            obj.frameRate, 1/obj.frameRate)
    if obj.runningSpeed is not None:
        for blockInd, goStim in enumerate(obj.blockStimRewarded):
            blockTrials = obj.trialBlock == blockInd + 1
            nogoStim = np.unique(obj.trialStim[blockTrials & obj.nogoTrials])
            fig = plt.figure(figsize=(8, 8))
            fig.suptitle('block ' + str(blockInd+1) + ': go=' +
                         goStim + ', nogo=' + str(nogoStim))
            gs = matplotlib.gridspec.GridSpec(2, 2)
            axs = []
            ymax = 1
            for trials, trialType in zip((obj.goTrials, obj.nogoTrials, obj.autoRewarded, obj.catchTrials),
                                         ('go', 'no-go', 'auto reward', 'catch')):
                trials = trials & blockTrials
                i = 0 if trialType in ('go', 'no-go') else 1
                j = 0 if trialType in ('go', 'auto reward') else 1
                ax = fig.add_subplot(gs[i, j])
                ax.add_patch(matplotlib.patches.Rectangle(
                    [-obj.quiescentFrames/obj.frameRate, 0], width=obj.quiescentFrames/obj.frameRate, height=100, facecolor='r', edgecolor=None, alpha=0.2, zorder=0))
                ax.add_patch(matplotlib.patches.Rectangle([obj.responseWindowTime[0], 0], width=np.diff(
                    obj.responseWindowTime), height=100, facecolor='g', edgecolor=None, alpha=0.2, zorder=0))
                if trials.sum() > 0:
                    speed = []
                    for st in obj.stimStartTimes[trials]:
                        if st >= preTime and st+postTime <= obj.frameTimes[-1]:
                            i = (obj.frameTimes >= st -
                                 preTime) & (obj.frameTimes <= st+postTime)
                            speed.append(
                                np.interp(runPlotTime, obj.frameTimes[i]-st, obj.runningSpeed[i]))
                    meanSpeed = np.nanmean(speed, axis=0)
                    ymax = max(ymax, meanSpeed.max())
                    ax.plot(runPlotTime, meanSpeed)
                for side in ('right', 'top'):
                    ax.spines[side].set_visible(False)
                ax.tick_params(direction='out', top=False, right=False)
                ax.set_xlim([-preTime, postTime])
                ax.set_xlabel('time from stimulus onset (s)')
                ax.set_ylabel('mean running speed (cm/s)')
                ax.set_title(trialType + ' trials (n=' + str(trials.sum()) +
                             '), engaged (n=' + str(obj.engagedTrials[trials].sum()) + ')')
                axs.append(ax)
            for ax in axs:
                ax.set_ylim([0, 1.05*ymax])
            fig.tight_layout(rect=[0, 0.03, 1, 0.95])

    return fig


def generate_frame_intervals(behavior_filepath: str):
    obj = DynRoutData()
    obj.loadBehavData(behavior_filepath)

    longFrames = obj.frameIntervals > 1.5/obj.frameRate

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    bins = np.arange(-0.5/obj.frameRate,
                     obj.frameIntervals.max()+1/obj.frameRate, 1/obj.frameRate)
    ax.hist(obj.frameIntervals, bins=bins, color='k')
    for side in ('right', 'top'):
        ax.spines[side].set_visible(False)
    ax.tick_params(direction='out', top=False, right=False)
    ax.set_yscale('log')
    ax.set_xlabel('frame interval (s)')
    ax.set_ylabel('count')
    ax.set_title(str(round(100 * longFrames.sum() /
                 longFrames.size, 2)) + '% of frames long')
    plt.tight_layout()

    return fig


def generate_quiescent_violations(behavior_filepath: str):
    obj = DynRoutData()
    obj.loadBehavData(behavior_filepath)

    trialQuiescentViolations = []
    for sf, ef in zip(obj.trialStartFrame, obj.trialEndFrame):
        trialQuiescentViolations.append(np.sum(
            (obj.quiescentViolationFrames > sf) & (obj.quiescentViolationFrames < ef)))

    fig = plt.figure(figsize=(6, 8))
    ax = fig.add_subplot(2, 1, 1)
    if obj.quiescentViolationFrames.size > 0:
        ax.plot(obj.frameTimes[obj.quiescentViolationFrames], np.arange(
            obj.quiescentViolationFrames.size)+1, 'k')
    for side in ('right', 'top'):
        ax.spines[side].set_visible(False)
    ax.tick_params(direction='out', top=False, right=False)
    ax.set_xlabel('time (s)')
    ax.set_ylabel('quiescent period violations')

    ax = fig.add_subplot(2, 1, 2)
    bins = np.arange(-0.5, max(trialQuiescentViolations)+1, 1)
    ax.hist(trialQuiescentViolations, bins=bins, color='k')
    for side in ('right', 'top'):
        ax.spines[side].set_visible(False)
    ax.tick_params(direction='out', top=False, right=False)
    ax.set_xlabel('quiescent period violations per trial')
    ax.set_ylabel('trials')
    plt.tight_layout()

    return fig


def generate_inter_trial_intervals(behavior_filepath: str):
    obj = DynRoutData()
    obj.loadBehavData(behavior_filepath)

    interTrialIntervals = np.diff(obj.frameTimes[obj.stimStartFrame])

    trialQuiescentViolations = []
    for sf, ef in zip(obj.trialStartFrame, obj.trialEndFrame):
        trialQuiescentViolations.append(np.sum(
            (obj.quiescentViolationFrames > sf) & (obj.quiescentViolationFrames < ef)))

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    bins = np.arange(interTrialIntervals.max()+1)
    ax.hist(interTrialIntervals, bins=bins, color='k', label='all trials')
    ax.hist(interTrialIntervals[np.array(trialQuiescentViolations[1:]) == 0],
            bins=bins, color='0.5', label='trials without quiescent period violations')
    for side in ('right', 'top'):
        ax.spines[side].set_visible(False)
    ax.tick_params(direction='out', top=False, right=False)
    ax.set_xlim([0, interTrialIntervals.max()+1])
    ax.set_xlabel('inter-trial interval (s)')
    ax.set_ylabel('trials')
    ax.legend()
    plt.tight_layout()

    return fig


def generate_running_speed(behavior_filepath: str):
    obj = DynRoutData()
    obj.loadBehavData(behavior_filepath)
    if obj.runningSpeed is None:
        return

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(obj.frameTimes, obj.runningSpeed[:obj.frameTimes.size], 'k')
    for side in ('right', 'top'):
        ax.spines[side].set_visible(False)
    ax.tick_params(direction='out', top=False, right=False)
    ax.set_xlim([0, obj.frameTimes[-1]])
    ax.set_xlabel('time (s)')
    ax.set_ylabel('running speed (cm/s)')
    plt.tight_layout()
    return fig


def generate_running_speed_binned(behavior_filepath: str, bin_size = 60):
    obj = DynRoutData()
    obj.loadBehavData(behavior_filepath)
    if obj.runningSpeed is None:
        return

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    binned_frame_times = []
    binned_running_speed = []
    for i in range(0, obj.frameTimes.size, bin_size):
        binned_frame_times.append(obj.frameTimes[i+bin_size-1])
        binned_running_speed.append(
            np.nanmean(obj.runningSpeed[i:i+bin_size])
        )
    
    # print(binned_frame_times)
    # print(binned_running_speed)
    ax.plot(binned_frame_times, binned_running_speed, 'k')
    for side in ('right', 'top'):
        ax.spines[side].set_visible(False)
    ax.tick_params(direction='out', top=False, right=False)
    ax.set_xlim([0, obj.frameTimes[-1]])
    ax.set_xlabel('time (s)')
    ax.set_ylabel('running speed (cm/s)')
    plt.tight_layout()
    return fig


def generate_cumulative_volume(behavior_filepath: str):
    obj = DynRoutData()
    obj.loadBehavData(behavior_filepath)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    trials = np.arange(obj.nTrials)
    cum_vol = list(np.cumsum(obj.rewardSize))
    cum_vol_inter_trial = []
    prev_cum_vol = 0
    for trial in trials:
        if obj.trialRewarded[trial]:
            prev_cum_vol = cum_vol.pop(0)
        cum_vol_inter_trial.append(prev_cum_vol)
    
    ax.plot(trials, cum_vol_inter_trial)
    ax.tick_params(direction='out', top=False, right=False)
    ax.set_ylim([0, 5.0])
    ax.set_xlabel('trials')
    ax.set_ylabel('cumulative volume (mL)')
    ax.legend()
    plt.tight_layout()
    return fig


def generate_cumulative_reward_count(behavior_filepath: str):
    obj = DynRoutData()
    obj.loadBehavData(behavior_filepath)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    trials = np.arange(obj.nTrials)
    reward_count = list(np.cumsum(obj.rewardSize))
    reward_count_trialwise = []
    prev_reward_count = 0
    for trial in trials:
        if obj.trialRewarded[trial]:
            prev_reward_count = reward_count.pop(0)
        reward_count_trialwise.append(prev_reward_count)
    
    ax.plot(trials, reward_count_trialwise)
    ax.tick_params(direction='out', top=False, right=False)
    ax.set_ylim([0, 5.0])
    ax.set_xlabel('trials')
    ax.set_ylabel('cumulative reward count')
    ax.legend()
    plt.tight_layout()
    return fig


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("behavior_filepath", type=str)

    args = parser.parse_args()

    data = h5py.File(args.behavior_filepath, "r")

    # lick raster for all trials
    lick_raster = generate_lick_raster_all_trials(args.behavior_filepath)

    # lick latency
    lick_latency = generate_lick_latency(args.behavior_filepath)

    # mean running speed for each block of trials
    run_speed_mean_block = generate_run_speed_mean_block(
        args.behavior_filepath)

    # frame intervals
    frame_intervals = generate_frame_intervals(args.behavior_filepath)

    # quiescent violations
    quiescent_violations = generate_quiescent_violations(
        args.behavior_filepath)

    # quiescent inter-trial intervals
    inter_trial_intervals = generate_inter_trial_intervals(
        args.behavior_filepath)

    # running speed
    running_speed = generate_running_speed(args.behavior_filepath)

    # running speed binned
    running_speed = generate_running_speed_binned(args.behavior_filepath)

    # cumulative volume
    cumulative_volume = generate_cumulative_volume(args.behavior_filepath)

    # cumulative rewards
    cumulative_rewards = generate_cumulative_reward_count(args.behavior_filepath)

    plt.show(block=True)
