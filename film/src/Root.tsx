import {Composition} from 'remotion';
import {DoorTest, DURATION_S} from './DoorTest';

const FPS = 30;

export const Root: React.FC = () => (
  <>
    <Composition id="DoorTest" component={DoorTest} durationInFrames={DURATION_S * FPS} fps={FPS} width={1920} height={1080} />
    <Composition id="DoorTest45" component={DoorTest} durationInFrames={DURATION_S * FPS} fps={FPS} width={1080} height={1350} />
  </>
);
