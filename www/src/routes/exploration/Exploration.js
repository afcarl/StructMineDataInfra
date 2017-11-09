import React, { Component } from 'react'
import {TreeList} from 'react-treeview-mui'
import FlatButton from 'material-ui/FlatButton';

import withStyles from 'isomorphic-style-loader/lib/withStyles';
import s from './Exploration.css';
import SearchBar from './SearchBar';
import {
  Step,
  Stepper,
  StepLabel,
} from 'material-ui/Stepper';

class Exploration extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      activeStep: 0,
    };
  }

  render() {
    const leftLinkComponent = (
      <a
        href="#"
        onClick={(event) => {
          event.preventDefault();
        }}
        >(example)</a>
      );
      const rightLinkComponent = this.state.activeStep >= 1 ? (
        <a
          href="#"
          onClick={(event) => {
            event.preventDefault();
          }}
          >(example)</a>
        ) : null;
        return (
          <div
            className={s.root}
            style={{display: 'flex', justifyContent: 'center', alignItems: 'center'}}
          >
            <div className={s.container}>
              <span className={s.title} >Life-iNet</span>
              <SearchBar
                style={{marginTop: 8}}
                onActiveStepChange={(activeStep) => this.setState({activeStep: activeStep})}
              />
              <Stepper activeStep={this.state.activeStep}>
                <Step>
                  <StepLabel>
                    Select Left Entities &nbsp;
                    {leftLinkComponent}
                  </StepLabel>
                </Step>
                <Step>
                  <StepLabel>
                    Select Right Entities &nbsp;
                    {rightLinkComponent}
                  </StepLabel>
                </Step>
                <Step>
                  <StepLabel>Choose Relationship between Entities</StepLabel>
                </Step>
                </Stepper>
              </div>
            </div>
          );
        }

      }

      export default withStyles(s)(Exploration);
