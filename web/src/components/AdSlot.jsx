export default function AdSlot({ size = 'leaderboard', style = {} }) {
  return (
    <div
      id="frame"
      style={{ width: '100%', margin: 'auto', position: 'relative', zIndex: 99998, ...style }}
    >
      <iframe
        data-aa="2437407"
        src="//acceptable.a-ads.com/2437407/?size=Adaptive"
        style={{
          border: 0, padding: 0, width: '70%', height: 'auto',
          overflow: 'hidden', display: 'block', margin: 'auto',
        }}
        scrolling="no"
        title="advertisement"
      />
    </div>
  )
}
